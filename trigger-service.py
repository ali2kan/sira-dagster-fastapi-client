from fastapi import FastAPI, HTTPException
from typing import Optional
import httpx
import os
from pydantic import BaseModel
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Dagster Job Trigger Service")

# Configuration
DAGSTER_GRAPHQL_URL = os.getenv("DAGSTER_GRAPHQL_URL", "http://localhost:3000/graphql")
API_KEY = os.getenv("API_KEY")  # Optional API key for basic security

class JobLaunchRequest(BaseModel):
    job_name: str
    run_config: Optional[dict] = None
    tags: Optional[dict] = None
    api_key: Optional[str] = None

async def launch_dagster_job(job_name: str, run_config: Optional[dict] = None, tags: Optional[dict] = None) -> dict:
    """
    Launch a Dagster job using the GraphQL API
    """
    # Add default tags if none provided
    if tags is None:
        tags = {}
    tags.update({
        "triggered_by": "external_api",
        "trigger_time": datetime.utcnow().isoformat()
    })

    # GraphQL mutation for launching a job
    mutation = """
    mutation LaunchPipelineExecution(
        $jobName: String!
        $runConfig: RunConfigData
        $tags: [InputTagKeyValue!]
    ) {
        launchPipelineExecution(
            executionParams: {
                selector: { name: $jobName }
                runConfigData: $runConfig
                tags: $tags
            }
        ) {
            __typename
            ... on LaunchPipelineRunSuccess {
                run {
                    runId
                    status
                }
            }
            ... on PythonError {
                message
                stack
            }
            ... on InvalidStepError {
                invalidStepKey
            }
        }
    }
    """

    # Prepare variables for GraphQL query
    variables = {
        "jobName": job_name,
        "runConfig": run_config or {},
        "tags": [{"key": k, "value": str(v)} for k, v in tags.items()]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                DAGSTER_GRAPHQL_URL,
                json={"query": mutation, "variables": variables},
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if "errors" in result:
                logger.error(f"GraphQL errors: {result['errors']}")
                raise HTTPException(status_code=400, detail=str(result["errors"]))
                
            return result["data"]["launchPipelineExecution"]
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to communicate with Dagster: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/trigger/{job_name}")
async def trigger_job(job_name: str, request: JobLaunchRequest):
    """
    Trigger a Dagster job by name with optional configuration
    """
    # Validate API key if configured
    if API_KEY and request.api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info(f"Triggering job: {job_name}")
    
    try:
        result = await launch_dagster_job(
            job_name=job_name,
            run_config=request.run_config,
            tags=request.tags
        )
        
        logger.info(f"Job launch result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to trigger job {job_name}: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)