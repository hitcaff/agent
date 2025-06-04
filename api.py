from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import run_agent
import logging
import asyncio
from pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("Running pipeline on startup")
    await run_pipeline()

class QueryRequest(BaseModel):
    query: str

@app.post("/chat")
async def chat_with_agent(request: QueryRequest):
    try:
        response = await run_agent(request.query)
        return {"response": response}
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))