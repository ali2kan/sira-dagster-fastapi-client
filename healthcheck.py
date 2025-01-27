from typing import Dict

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}
