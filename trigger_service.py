import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Configuration class
class Settings:
    def __init__(self):
        self.DAGSTER_HOST = os.getenv("DAGSTER_HOST", "dagster-webserver")
        self.DAGSTER_PORT = int(os.getenv("DAGSTER_PORT", "3000"))
        self.DAGSTER_GRAPHQL_URL = os.getenv(
            "DAGSTER_GRAPHQL_URL", f"http://{self.DAGSTER_HOST}:{self.DAGSTER_PORT}/graphql"
        )
        self.API_KEY = os.getenv("API_KEY")
        self.REPOSITORY_LOCATION = os.getenv("DAGSTER_REPOSITORY_LOCATION", "")
        self.REPOSITORY_NAME = os.getenv("DAGSTER_REPOSITORY_NAME", "__repository__")


@lru_cache()
def get_settings():
    return Settings()


# Initialize FastAPI
app = FastAPI(title="Dagster Job Trigger Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class JobLaunchRequest(BaseModel):
    """Request model for launching a job"""

    job_name: str = Field(..., description="Name of the Dagster job to run")
    run_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the job run")


async def verify_api_key(api_key: str = Depends(api_key_header)) -> None:
    """Verify API key if configured"""
    settings = get_settings()
    if settings.API_KEY:
        if not api_key or api_key != settings.API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def launch_dagster_job(
    job_name: str,
    run_config: Optional[Dict[str, Any]] = None,
) -> dict:
    """Launch a Dagster job using the GraphQL API"""
    settings = get_settings()

    # Use the working mutation structure
    mutation = """
    mutation LaunchRunMutation(
        $repositoryLocationName: String!
        $repositoryName: String!
        $jobName: String!
        $runConfigData: RunConfigData!
        $pipelineName: String!
    ) {
        launchRun(
            executionParams: {
                selector: {
                    repositoryLocationName: $repositoryLocationName
                    repositoryName: $repositoryName
                    jobName: $jobName
                    pipelineName: $pipelineName
                }
                runConfigData: $runConfigData
            }
        ) {
            __typename
            ... on LaunchRunSuccess {
                run {
                    runId
                }
            }
            ... on RunConfigValidationInvalid {
                errors {
                    message
                    reason
                }
            }
            ... on PythonError {
                message
            }
        }
    }
    """

    # Prepare variables
    variables = {
        "repositoryLocationName": settings.REPOSITORY_LOCATION,
        "repositoryName": settings.REPOSITORY_NAME,
        "jobName": job_name,
        "pipelineName": job_name,  # Using job_name as pipeline name
        "runConfigData": run_config if run_config is not None else "",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.DAGSTER_GRAPHQL_URL, json={"query": mutation, "variables": variables}, timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                logger.error(f"GraphQL errors: {json.dumps(result['errors'])}")
                raise HTTPException(status_code=400, detail={"errors": result["errors"]})

            launch_result = result["data"]["launchRun"]

            # Handle different response types
            if launch_result["__typename"] == "RunConfigValidationInvalid":
                error_messages = [error["message"] for error in launch_result["errors"]]
                raise HTTPException(status_code=400, detail={"errors": error_messages})
            elif launch_result["__typename"] == "PythonError":
                raise HTTPException(status_code=500, detail=launch_result["message"])

            return launch_result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to communicate with Dagster: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/trigger/{job_name}")
async def trigger_job(job_name: str, request: JobLaunchRequest, _=Depends(verify_api_key)):
    """Trigger a Dagster job by name"""
    logger.info(f"Triggering job: {job_name}")

    try:
        result = await launch_dagster_job(
            job_name=job_name.strip(),  # Remove any trailing spaces
            run_config=request.run_config,
        )

        logger.info(f"Job launch result: {json.dumps(result)}")
        return result

    except Exception as e:
        logger.error(f"Failed to trigger job {job_name}: {str(e)}")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
