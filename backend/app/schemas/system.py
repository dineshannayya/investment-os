from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Liveness probe response.
    """

    status: str = Field(
        ...,
        examples=["ok"],
    )


class ReadyServices(BaseModel):
    """
    Readiness status of external services.
    """

    database: str = Field(examples=["not_configured"])

    redis: str = Field(examples=["not_configured"])

    llm: str = Field(examples=["not_configured"])


class ReadyResponse(BaseModel):
    """
    Readiness probe response.
    """

    status: str = Field(
        ...,
        examples=["ready"],
    )

    services: ReadyServices


class VersionResponse(BaseModel):
    """
    Version information.
    """

    application: str

    version: str

    environment: str
