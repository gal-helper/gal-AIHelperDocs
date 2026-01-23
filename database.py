import asyncpg
import json
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from config import config
from ai_service import ai_service  # 正确导入

logger = logging.getLogger(__name__)

class DatabaseService:
    
    def __init__(self):
        self.pool = None
    
    async def connect(self) -> bool:
        try:
            basic_params = {
                'host': config.DB_HOST,
                'port': config.DB_PORT,
                'database': config.DB_NAME,
                'user': config.DB_USER,
                'password': config.DB_PASSWORD
            }
            
            self.pool = await asyncpg.create_pool(
                **basic_params,
                min_size=config.DB_POOL_MIN_SIZE,
                max_size=config.DB_POOL_MAX_SIZE,
                command_timeout=config.DB_POOL_TIMEOUT
            )
            logger.info(f"Connected to database: {config.DB_HOST}/{config.DB_NAME}")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    async def initialize_tables(self) -> bool:
        try:
            async with self.pool.acquire() as conn:
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    logger.info("pgvector extension created or already exists")
                except Exception as e:
                    logger.warning(f"Cannot create pgvector extension: {e}")
                    return False
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        file_type VARCHAR(10),
                        content TEXT NOT NULL,
                        content_vector vector(1536),
                        token_count INTEGER DEFAULT 0,
                        file_metadata JSONB DEFAULT '{}',
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS query_history (
                        id SERIAL PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer TEXT,
                        used_documents TEXT[],
                        response_time FLOAT,
                        asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                try:
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_documents_vector 
                        ON documents USING ivfflat (content_vector vector_cosine_ops);
                    """)
                    logger.info("Vector index created or already exists")
                except Exception as e:
                    logger.warning(f"Cannot create vector index: {e}")
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_filename 
                    ON documents(filename);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_query_asked_at 
                    ON query_history(asked_at DESC);
                """)
                
                logger.info("Database tables initialized successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize tables: {e}")
            return False
    
    async def save_document(self, filename: str, content: str, file_type: str, metadata: Dict[str, Any] = None) -> Optional[int]:
        try:
            # 使用 ai_service 计算 token_count
            token_count = ai_service.count_tokens(content)
            
            async with self.pool.acquire() as conn:
                existing = await conn.fetchrow(
                    "SELECT id FROM documents WHERE filename = $1",
                    filename
                )
                
                if existing:
                    logger.info(f"Document already exists: {filename}")
                    return existing['id']
                
                doc_result = await conn.fetchrow("""
                    INSERT INTO documents (filename, file_type, content, token_count, file_metadata, uploaded_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """, filename, file_type, content, token_count, 
                   json.dumps(metadata or {}), datetime.now())
                
                doc_id = doc_result['id']
                logger.info(f"Document saved: {filename} (ID: {doc_id}, Tokens: {token_count})")
                return doc_id
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return None
    
    async def update_document_embedding(self, doc_id: int, embedding: List[float]) -> bool:
        try:
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE documents 
                    SET content_vector = $1::vector
                    WHERE id = $2
                """, embedding_str, doc_id)
                
                return True
        except Exception as e:
            logger.error(f"Failed to update embedding: {e}")
            return False
    
    async def search_similar_documents(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        try:
            query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            async with self.pool.acquire() as conn:
                results = await conn.fetch(f"""
                    SELECT 
                        id,
                        filename,
                        content,
                        file_metadata,
                        1 - (content_vector <=> $1::vector) as similarity
                    FROM documents
                    WHERE content_vector IS NOT NULL
                    AND 1 - (content_vector <=> $1::vector) >= $2
                    ORDER BY content_vector <=> $1::vector
                    LIMIT $3
                """, query_embedding_str, config.SIMILARITY_THRESHOLD, limit)
                
                documents = []
                for row in results:
                    metadata = json.loads(row['file_metadata']) if row['file_metadata'] else {}
                    
                    documents.append({
                        'id': row['id'],
                        'filename': row['filename'],
                        'content': row['content'],
                        'metadata': metadata,
                        'similarity': float(row['similarity'])
                    })
                
                logger.info(f"Vector search found {len(documents)} documents (threshold: {config.SIMILARITY_THRESHOLD})")
                return documents
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def keyword_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            async with self.pool.acquire() as conn:
                results = await conn.fetch(f"""
                    SELECT 
                        id,
                        filename,
                        content,
                        file_metadata
                    FROM documents
                    WHERE content ILIKE '%' || $1 || '%'
                    LIMIT $2
                """, query, limit)
                
                documents = []
                for row in results:
                    metadata = json.loads(row['file_metadata']) if row['file_metadata'] else {}
                    documents.append({
                        'id': row['id'],
                        'filename': row['filename'],
                        'content': row['content'],
                        'metadata': metadata,
                        'similarity': 0.5
                    })
                
                return documents
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def save_query_history(self, question: str, answer: str, 
                                used_docs: List[str] = None, 
                                response_time: float = 0.0) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO query_history 
                    (question, answer, used_documents, response_time, asked_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, question, answer, used_docs or [], response_time, datetime.now())
                
                return True
        except Exception as e:
            logger.error(f"Failed to save query history: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        try:
            async with self.pool.acquire() as conn:
                stats = {}
                
                stats['documents'] = await conn.fetchval("SELECT COUNT(*) FROM documents")
                stats['vectorized_documents'] = await conn.fetchval(
                    "SELECT COUNT(*) FROM documents WHERE content_vector IS NOT NULL"
                )
                stats['queries'] = await conn.fetchval("SELECT COUNT(*) FROM query_history")
                
                recent = await conn.fetch("""
                    SELECT question, answer, asked_at 
                    FROM query_history 
                    ORDER BY asked_at DESC 
                    LIMIT 10
                """)
                
                stats['recent_queries'] = [
                    {
                        'question': row['question'][:100] + '...' if len(row['question']) > 100 else row['question'],
                        'answer': row['answer'][:100] + '...' if row['answer'] and len(row['answer']) > 100 else row['answer'],
                        'asked_at': row['asked_at'].isoformat()
                    }
                    for row in recent
                ]
                
                file_types = await conn.fetch("""
                    SELECT file_type, COUNT(*) as count 
                    FROM documents 
                    GROUP BY file_type
                """)
                
                stats['file_types'] = {row['file_type']: row['count'] for row in file_types}
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'error': str(e)}

db_service = DatabaseService()