import logging
import os

import strawberry
from dagster_graphql import DagsterGraphQLClient, DagsterGraphQLClientError
from fastapi import FastAPI, HTTPException
from strawberry.fastapi import GraphQLRouter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Dagster Job Trigger Service")

# Configure Dagster client
DAGSTER_HOST = os.getenv("DAGSTER_HOST", "10.10.10.34")
DAGSTER_PORT = int(os.getenv("DAGSTER_PORT", "3000"))

# Create the client with proper URL format
client = DagsterGraphQLClient(f"http://{DAGSTER_HOST}", port_number=DAGSTER_PORT)


@strawberry.type
class JobResponse:
    status: str
    run_id: str
    job_name: str


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def trigger_job(self, job_name: str) -> JobResponse:
        try:
            logger.info(f"Attempting to trigger job: {job_name}")

            new_run_id = client.submit_job_execution(
                job_name.strip(),
                run_config={},
            )

            logger.info(f"Successfully triggered job {job_name} with run_id: {new_run_id}")
            return JobResponse(status="success", run_id=new_run_id, job_name=job_name)

        except DagsterGraphQLClientError as exc:
            error_msg = f"Dagster GraphQL error: {str(exc)}"
            logger.error(error_msg)
            raise Exception(error_msg)


@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> str:
        return "healthy"


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

# Add the GraphQL router
app.include_router(graphql_app, prefix="/graphql")


# Keep the REST endpoint as well
@app.post("/trigger/{job_name}")
async def trigger_job_rest(job_name: str):
    """
    REST endpoint to trigger a Dagster job
    """
    try:
        logger.info(f"Attempting to trigger job via REST: {job_name}")

        new_run_id = client.submit_job_execution(
            job_name.strip(),
            run_config={},
        )

        logger.info(f"Successfully triggered job {job_name} with run_id: {new_run_id}")
        return {"status": "success", "run_id": new_run_id, "job_name": job_name}

    except DagsterGraphQLClientError as exc:
        error_msg = f"Dagster GraphQL error: {str(exc)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(exc), "job_name": job_name})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
