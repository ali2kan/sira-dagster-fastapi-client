from pydantic_settings import BaseSettings, SettingsConfigDict


class DagsterConfig(BaseSettings):
    """Dagster configuration settings"""

    DAGSTER_HOST: str = "10.10.10.34"
    DAGSTER_PORT: int = 3000
    TIMEOUT_SECONDS: int = 30

    # Repository settings
    REPOSITORY_LOCATION: str = "dlt_pipelines"
    REPOSITORY_NAME: str = "__repository__"

    # Job definitions
    AVAILABLE_JOBS = {
        "countries_job": {
            "description": "Update countries database from external source",
            "repository_location": REPOSITORY_LOCATION,  # Can be overridden per job
            "repository_name": REPOSITORY_NAME,
        },
        # Add new jobs here
        # "another_job": {
        #     "description": "Description of what this job does",
        #     "repository_location": "custom_location",  # Optional override
        #     "repository_name": "custom_repo",         # Optional override
        # },
    }

    @property
    def graphql_url(self) -> str:
        """Generate GraphQL URL from settings"""
        return f"http://{self.DAGSTER_HOST}:{self.DAGSTER_PORT}/graphql"

    model_config = SettingsConfigDict(env_prefix="DAGSTER_", validate_default=True)
