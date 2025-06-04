import sqlite3
import logging
import cohere
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

co = cohere.Client(os.getenv('COHERE_API_KEY'))

def query_db(query, doc_type=None):
    try:
        with sqlite3.connect('federal_register.db') as conn:
            cursor = conn.cursor()
            base_query = 'SELECT title, publication_date, type, abstract FROM documents WHERE 1=1'
            params = []
            if doc_type and doc_type != 'All':
                base_query += ' AND type = ?'
                params.append(doc_type)
            if 'recent' in query.lower() or 'new' in query.lower():
                base_query += ' AND publication_date LIKE ?'
                params.append('2024%')
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            logger.info(f"Query '{query}' with type '{doc_type}' returned {len(results)} documents")
            return [{'title': row[0], 'date': row[1], 'type': row[2], 'abstract': str(row[3])} for row in results]
    except Exception as e:
        logger.error(f'Database query failed: {e}')
        return []

def generate_response(query, doc_type=None):
    try:
        results = query_db(query, doc_type)
        if not results:
            return 'No documents found.'
        abstracts = [doc['abstract'] for doc in results if doc['abstract'] and doc['abstract'] != 'None']
        if not abstracts:
            return 'No abstracts available for the found documents.'
        cohere_response = co.summarize(text='\n'.join(abstracts), length='medium')
        response = 'Found documents:\n'
        for doc in results:
            response += f'- {doc["title"]} ({doc["date"]}, {doc["type"]}): {doc["abstract"]}\n'
        response += f'\nSummary: {cohere_response.summary}'
        return response
    except Exception as e:
        logger.error(f'Agent error: {e}')
        return f'Agent error: {str(e)}'
