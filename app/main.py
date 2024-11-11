import uvicorn
from fastapi import FastAPI
from routers import project_router
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Include routers
app.include_router(project_router.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the Project Management API"}

# Run in local environment please uncomment the below code
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level='debug', reload=True)