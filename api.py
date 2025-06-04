from fastapi import FastAPI
from pydantic import BaseModel
import logging
from agent import generate_response
from pipeline import run_pipeline
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

class Query(BaseModel):
    query: str

@app.on_event('startup')
async def startup_event():
    logger.info('Running pipeline on startup')
    await run_pipeline()

@app.post('/chat')
async def chat(query: Query):
    doc_type = None
    query_text = query.query
    if '(type:' in query_text.lower():
        parts = query_text.split('(type:')
        query_text = parts[0].strip()
        doc_type = parts[1].replace(')', '').strip()
    elif 'executive order' in query_text.lower():
        doc_type = 'Executive Order'
    try:
        response = generate_response(query_text, doc_type)
        return {'response': response}
    except Exception as e:
        logger.error(f'API error: {str(e)}')
        return {'response': f'Agent error: {str(e)}'}
