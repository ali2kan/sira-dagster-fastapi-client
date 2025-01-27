import logging
import os
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
DAGSTER_HOST = os.getenv("DAGSTER_HOST", "localhost")
DAGSTER_PORT = os.getenv("DAGSTER_PORT", "3000")
REPOSITORY_LOCATION = os.getenv("REPOSITORY_LOCATION", "dlt_pipelines")
REPOSITORY_NAME = os.getenv("REPOSITORY_NAME", "__repository__")
API_KEY = os.getenv("API_KEY")

logger.info(f"Starting service with API key configured: {API_KEY}")

app = FastAPI(title="Dagster Job Trigger Service")


def verify_api_key(request: Request, api_key_param: Optional[str] = None):
    """Verify API key from either header or URL parameter"""
    # Check header first
    api_key_header = request.headers.get("X-API-Key")

    # Check URL parameter next
    api_key = api_key_header or api_key_param

    logger.info(f"Checking API key (Header: {api_key_header}, URL: {api_key_param})")

    if not API_KEY:
        logger.error("No API key configured in environment!")
        raise HTTPException(status_code=500, detail="API Key not configured")

    if not api_key or api_key != API_KEY:
        logger.warning(f"Invalid API key attempt: {api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")

    logger.info("API key verified successfully")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "api_key_configured": str(API_KEY), "dagster_host": DAGSTER_HOST}


@app.post("/trigger/{job_name}")
async def trigger_job(
    request: Request, job_name: str, api_key: Optional[str] = None  # Optional URL parameter
) -> Dict[str, str]:
    """
    Trigger a Dagster job by name.
    API key can be provided either:
    - In X-API-Key header
    - As 'api_key' URL parameter
    """
    verify_api_key(request, api_key)

    try:
        logger.info(f"Attempting to trigger job: {job_name}")
        graphql_url = f"http://{DAGSTER_HOST}:{DAGSTER_PORT}/graphql"

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
                "repositoryLocationName": REPOSITORY_LOCATION,
                "repositoryName": REPOSITORY_NAME,
                "jobName": job_name.strip(),
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(graphql_url, json=query)
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
