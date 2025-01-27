import logging
import os

import httpx
from fastapi import FastAPI, HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Dagster Job Trigger Service")

# Configure Dagster client
DAGSTER_HOST = os.getenv("DAGSTER_HOST", "10.10.10.34")
DAGSTER_PORT = int(os.getenv("DAGSTER_PORT", "3000"))
GRAPHQL_URL = f"http://{DAGSTER_HOST}:{DAGSTER_PORT}/graphql"


@app.post("/trigger/{job_name}")
async def trigger_job(job_name: str):
    """Trigger a Dagster job by name"""
    try:
        logger.info(f"Attempting to trigger job: {job_name}")

        # Use the exact working mutation
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
                "repositoryLocationName": "dlt_pipelines",
                "repositoryName": "__repository__",
                "jobName": job_name.strip(),
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GRAPHQL_URL, json=query)
            result = response.json()

            if "errors" in result:
                raise Exception(result["errors"][0]["message"])

            run_id = result["data"]["launchRun"]["run"]["runId"]
            return {"status": "success", "run_id": run_id, "job_name": job_name}

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e), "job_name": job_name})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
