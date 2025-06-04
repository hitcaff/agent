import aiohttp
import sqlite3
import json
import requests
import os
from datetime import datetime, timedelta
import asyncio
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://www.federalregister.gov/api/v1/documents.json"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

MOCK_DATA = [
    {
        "document_number": "2024-12345",
        "title": "Executive Order on Environmental Policy",
        "publication_date": "2024-05-01",
        "type": "Executive Order",
        "abstract": "Directs federal agencies to prioritize environmental regulations."
    },
    {
        "document_number": "2024-12346",
        "title": "Proposed Rule on Workforce Development",
        "publication_date": "2024-05-15",
        "type": "Proposed Rule",
        "abstract": "Establishes new training programs for federal employees."
    }
]

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('federal_register.db')
    try:
        yield conn
    finally:
        conn.close()

async def download_data(start_date, end_date):
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "publication_date_gte": start_date,
                "publication_date_lte": end_date,
                "per_page": 100,
                "type": "Executive Order"
            }
            async with session.get(API_URL, params=params) as response:
                response.raise_for_status()
                raw_data = await response.json()
                raw_file = os.path.join(DATA_DIR, f"raw_{start_date}.json")
                with open(raw_file, "w") as f:
                    json.dump(raw_data, f)
                results = raw_data.get("results", [])
                if not results:
                    logger.warning("No Executive Order data from API, using mock data.")
                    return MOCK_DATA
                logger.info(f"Downloaded {len(results)} Executive Order documents from API.")
                return results
    except aiohttp.ClientError as e:
        logger.error(f"Error downloading data: {e}")
        return MOCK_DATA

def process_data(raw_data):
    processed = []
    for doc in raw_data:
        processed.append({
            "document_number": doc.get("document_number", ""),
            "title": doc.get("title", ""),
            "publication_date": doc.get("publication_date", ""),
            "type": doc.get("type", ""),
            "abstract": doc.get("abstract", "")
        })
    processed_file = os.path.join(DATA_DIR, f"processed_{datetime.now().strftime('%Y%m%d')}.json")
    with open(processed_file, "w") as f:
        json.dump(processed, f)
    return processed

async def store_to_sqlite(data):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS documents (document_number TEXT PRIMARY KEY, title TEXT, publication_date TEXT, type TEXT, abstract TEXT)")
            for doc in data:
                cursor.execute("INSERT OR REPLACE INTO documents (document_number, title, publication_date, type, abstract) VALUES (?, ?, ?, ?, ?)", 
                              (doc['document_number'], doc['title'], doc['publication_date'], doc['type'], doc['abstract']))
            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM documents")
            count = cursor.fetchone()[0]
            logger.info(f"Stored {count} documents in database")
            cursor.execute("SELECT * FROM documents WHERE type = 'Executive Order' LIMIT 1")
            sample = cursor.fetchone()
            logger.info(f"Sample document: {sample}")
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")

def clean_old_files():
    threshold = datetime.now() - timedelta(days=7)
    for file in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, file)
        if os.path.isfile(file_path):
            file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_date < threshold:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")

async def run_pipeline():
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = "2024-01-01"
        raw_data = await download_data(start_date, end_date)
        if not raw_data:
            logger.error("No data downloaded.")
            return
        processed_data = process_data(raw_data)
        await store_to_sqlite(processed_data)
        clean_old_files()
        logger.info(f"Pipeline completed. Stored {len(processed_data)} documents.")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
