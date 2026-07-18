from fastapi import FastAPI

app = FastAPI(
    title="Investment OS",
    description="AI-powered Investment Operating System",
    version="0.1.0"
)


@app.get("/")
async def root():
    return {
        "application": "Investment OS",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.get("/version")
async def version():
    return {
        "version": "0.1.0"
    }
