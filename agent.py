import sqlite3
import logging
import cohere
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
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
            return [{'title': row[0], 'date': row[1], 'type': row[2], 'abstract': str(row[3] or '')} for row in results]
    except sqlite3.Error as e:
        logger.error(f"Database query failed: {str(e)}")
        return []

def generate_response(query, doc_type=None):
    try:
        results = query_db(query, doc_type)
        if not results:
            logger.warning("No documents found in database.")
            return 'No documents found.'
        abstracts = [doc['abstract'] for doc in results if doc['abstract'].strip()]
        if not abstracts:
            logger.warning("No valid abstracts found.")
            return 'No abstracts available for the found documents.'
        combined_text = '\n'.join(abstracts)
        response = 'Found documents:\n'
        for doc in results:
            response += f"- {doc['title']} ({doc['date']}, {doc['type']}): {doc['abstract'][:200]}...\n"
        if len(combined_text) < 250:
            logger.warning(f"Combined text too short ({len(combined_text)} chars). Skipping Cohere summarization.")
            response += '\nSummary: Text too short to summarize.'
            return response
        try:
            cohere_response = co.summarize(text=combined_text, length='medium')
            response += f'\nSummary: {cohere_response.summary}'
        except cohere.CohereAPIError as e:
            logger.error(f"Cohere API error: {str(e)}")
            response += '\nSummary: Unable to generate summary due to API error.'
        return response
    except Exception as e:
        logger.error(f"Response generation failed: {str(e)}")
        return f'Agent error: {str(e)}'
