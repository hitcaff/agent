import json
import sqlite3
import logging
import asyncio
from datetime import datetime
from contextlib import contextmanager
import aiohttp
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('federal_register.db')
    try:
        yield conn
    finally:
        conn.close()

async def fetch_documents_from_db(query: str, start_date: str, end_date: str, doc_type: str = None):
    try:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}
        if not query.strip():
            return {"error": "Query cannot be empty."}
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT document_number, title, publication_date, type, abstract
                FROM documents
                WHERE publication_date BETWEEN ? AND ?
                AND (title LIKE ? OR abstract LIKE ?)
            """
            params = [start_date, end_date, f"%{query}%", f"%{query}%"]
            if doc_type:
                sql += " AND type = ?"
                params.append(doc_type)
            cursor.execute(sql, params)
            results = cursor.fetchall()
            return [{"document_number": r[0], "title": r[1], "publication_date": str(r[2]), "type": r[3], "abstract": r[4]} for r in results]
    except sqlite3.Error as e:
        logger.error(f"Database query failed: {e}")
        return {"error": f"Database query failed: {e}"}

async def summarize_text(text: str):
    try:
        if len(text) < 250:
            return text  # Skip summarization if text is too short
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.cohere.ai/v1/summarize",
                headers={"Authorization": f"Bearer {os.getenv('COHERE_API_KEY')}"},
                json={"text": text, "length": "short", "format": "paragraph"}
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result["summary"]
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return text  # Fallback to original text

async def run_agent(query: str):
    try:
        if not query.strip():
            return "Error: Query cannot be empty."
        # Parse query for doc_type
        doc_type = None
        if "(type:" in query:
            parts = query.split("(type:")
            query = parts[0].strip()
            doc_type = parts[1].replace(")", "").strip()
        # Fetch from database
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        result = await fetch_documents_from_db(query, start_date, end_date, doc_type)
        if isinstance(result, dict) and "error" in result:
            return result["error"]
        if not result:
            return "No documents found."
        # Summarize abstracts
        for doc in result:
            if doc.get("abstract"):
                doc["abstract"] = await summarize_text(doc["abstract"])
        # Format response
        output = "Found documents:\n"
        for doc in result:
            output += f"- {doc['title']} ({doc['publication_date']}, {doc['type']}): {doc['abstract']}\n"
        return output
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"Agent error: {str(e)}"

if __name__ == "__main__":
    test_query = "What are the new executive orders in 2024?"
    print(f"Query: {test_query}")
    print(f"Response: {asyncio.run(run_agent(test_query))}")