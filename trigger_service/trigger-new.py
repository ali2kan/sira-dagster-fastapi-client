import logging
from typing import Dict

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import DagsterConfig
from .security import verify_api_key

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Dagster Job Trigger Service",
    description="Secure API for triggering Dagster jobs",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize configuration
config = DagsterConfig()


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint - no authentication required."""
    return {"status": "healthy"}


@app.post("/trigger/{job_name}")
async def trigger_job(job_name: str, _=Depends(verify_api_key)) -> Dict[str, str]:  # Add authentication dependency
    """
    Trigger a Dagster job by name.
    Requires valid API key in X-API-Key header.
    """
    try:
        logger.info(f"Attempting to trigger job: {job_name}")

        query = {
            "query": """
            mutation LaunchRunMutation(
                $repositoryLocationName: String!
                $repositoryName: String!
                $jobName: String!
            ) {
                launchRun(
                    executionParams: {
                        selector: {
                            repositoryLocationName: $repositoryLocationName
                            repositoryName: $repositoryName
                            jobName: $jobName
                        }
                        runConfigData: {}
                    }
                ) {
                    __typename
                    ... on LaunchRunSuccess {
                        run {
                            runId
                        }
                    }
                }
            }
            """,
            "variables": {
                "repositoryLocationName": config.REPOSITORY_LOCATION,
                "repositoryName": config.REPOSITORY_NAME,
                "jobName": job_name.strip(),
            },
        }

        async with httpx.AsyncClient(timeout=config.TIMEOUT_SECONDS) as client:
            response = await client.post(config.graphql_url, json=query)
            result = response.json()

            if "errors" in result:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": result["errors"][0]["message"], "job_name": job_name},
                )

            run_id = result["data"]["launchRun"]["run"]["runId"]
            return {"status": "success", "run_id": run_id, "job_name": job_name}

    except Exception as e:
        logger.error(f"Error triggering job {job_name}: {str(e)}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e), "job_name": job_name})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
