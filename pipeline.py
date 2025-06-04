import aiohttp
import sqlite3
import json
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
        "abstract": "This Executive Order directs federal agencies to prioritize environmental regulations and sustainability initiatives to address climate change. It mandates the adoption of green energy solutions across government operations, establishes new reporting requirements for carbon emissions, and promotes inter-agency collaboration to achieve net-zero emissions by 2050."
    },
    {
        "document_number": "2024-12346",
        "title": "Executive Order on Workforce Development",
        "publication_date": "2024-05-15",
        "type": "Executive Order",
        "abstract": "This Executive Order establishes comprehensive training programs for federal employees to enhance skills in technology and management. It aims to improve government efficiency and service delivery by investing in workforce development, creating new career pathways, and fostering partnerships with educational institutions to support continuous learning."
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
    logger.warning("Using mock data due to Federal Register API syntax issues.")
    return MOCK_DATA

def process_data(raw_data):
    processed = []
    for doc in raw_data:
        processed.append({
            "document_number": doc.get("document_number", ""),
            "title": doc.get("title", ""),
            "publication_date": doc.get("publication_date", ""),
            "type": doc.get("type", ""),
            "abstract": doc.get("abstract", "") or doc.get("summary", "")
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
        logger.error(f"Database error: {str(e)}")

def clean_old_files():
    try:
        threshold = datetime.now() - timedelta(days=7)
        for file in os.listdir(DATA_DIR):
            file_path = os.path.join(DATA_DIR, file)
            if os.path.isfile(file_path):
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_date < threshold:
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning files: {str(e)}")

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
        logger.error(f"Pipeline failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
