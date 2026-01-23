import asyncio
import logging
import time
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import config
from ai_service import ai_service
from database import db_service

logger = logging.getLogger(__name__)

class TextProcessor:
    
    @staticmethod
    def process_file_content(filepath: str) -> List[Dict[str, Any]]:
        import os
        filename = os.path.basename(filepath)
        file_ext = os.path.splitext(filename)[1].lower()
        
        documents = []
        
        if filepath.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.strip():
                documents.append({
                    'filename': filename,
                    'file_type': 'txt',
                    'content': content,
                    'metadata': {
                        'file_type': 'txt',
                        'length': len(content)
                    }
                })
        
        elif filepath.endswith(('.xlsx', '.xls', '.csv')):
            try:
                if filepath.endswith('.csv'):
                    df = pd.read_csv(filepath)
                    sheet_name = 'CSV'
                    
                    for idx, row in df.iterrows():
                        row_content = row.to_string()
                        if row_content.strip():
                            documents.append({
                                'filename': f"{filename} - Row {idx+1}",
                                'file_type': 'excel',
                                'content': row_content,
                                'metadata': {
                                    'file_type': 'excel',
                                    'sheet': sheet_name,
                                    'row': idx + 1,
                                    'columns': len(df.columns),
                                    'original_file': filename
                                }
                            })
                else:
                    excel_file = pd.ExcelFile(filepath)
                    
                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(filepath, sheet_name=sheet_name)
                        
                        for idx, row in df.iterrows():
                            row_content = row.to_string()
                            if row_content.strip():
                                documents.append({
                                    'filename': f"{filename} - {sheet_name} - Row {idx+1}",
                                    'file_type': 'excel',
                                    'content': row_content,
                                    'metadata': {
                                        'file_type': 'excel',
                                        'sheet': sheet_name,
                                        'row': idx + 1,
                                        'columns': len(df.columns),
                                        'original_file': filename
                                    }
                                })
                
                logger.info(f"Excel file processed: {len(documents)} rows from {filename}")
                
            except Exception as e:
                logger.error(f"Error reading Excel file: {e}")
                raise
        
        return documents
    
    @staticmethod
    def build_rag_prompt(question: str, context_docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        if not context_docs:
            return [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": question}
            ]
        
        context_text = "\n\n".join([
            f"From document '{doc.get('filename', 'Unknown')}':\n{doc['content']}"
            for doc in context_docs
        ])
        
        return [
            {
                "role": "system", 
                "content": "You are a helpful AI assistant that answers questions based on the provided context. Answer the question based ONLY on the provided context. If the context doesn't contain relevant information, say I don't have enough information to answer this question based on the provided documents. Do not make up information."
            },
            {
                "role": "user", 
                "content": f"Context Information:\n{context_text}\n\nQuestion: {question}\n\nPlease answer the question based on the context above."
            }
        ]

class RAGProcessor:
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.initialized = False
    
    async def initialize(self) -> bool:
        try:
            logger.info("Initializing RAG processor...")
            
            test_embedding = await ai_service.get_embedding("test")
            logger.info(f"AI service initialized: {len(test_embedding)}D embeddings")
            
            if not await db_service.connect():
                logger.error("Failed to connect to database")
                return False
            
            if not await db_service.initialize_tables():
                logger.warning("Table initialization may have issues, continuing...")
            
            self.initialized = True
            logger.info("RAG processor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RAG processor: {e}")
            return False
    
    async def process_document(self, filepath: str) -> Dict[str, Any]:
        if not self.initialized:
            await self.initialize()
        
        result = {
            "success": False,
            "filename": "",
            "documents_processed": 0,
            "chunks": 0,
            "document_ids": [],
            "message": ""
        }
        
        try:
            import os
            filename = os.path.basename(filepath)
            result["filename"] = filename
            
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in config.SUPPORTED_EXTENSIONS:
                result["message"] = f"Unsupported file type: {file_ext}"
                return result
            
            documents = self.text_processor.process_file_content(filepath)
            
            if not documents:
                result["message"] = "No content found in file"
                return result
            
            logger.info(f"Processing {len(documents)} documents from {filename}")
            
            saved_ids = []
            for doc in documents:
                doc_id = await db_service.save_document(
                    doc['filename'], 
                    doc['content'], 
                    doc['file_type'], 
                    doc['metadata']
                )
                
                if doc_id:
                    saved_ids.append(doc_id)
                    
                    await self._generate_document_embedding(doc_id, doc['content'])
                else:
                    logger.warning(f"Failed to save document: {doc['filename']}")
            
            if saved_ids:
                result["success"] = True
                result["documents_processed"] = len(saved_ids)
                result["chunks"] = len(saved_ids)
                result["document_ids"] = saved_ids
                result["message"] = f"Processed {len(saved_ids)} documents"
                
                logger.info(f"Successfully processed {len(saved_ids)} documents from {filename}")
            else:
                result["message"] = "Failed to save any documents to database"
                logger.error(f"Failed to save any documents from: {filename}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def _generate_document_embedding(self, doc_id: int, content: str):
        try:
            embedding = await ai_service.get_embedding(content)
            
            if embedding:
                await db_service.update_document_embedding(doc_id, embedding)
                logger.info(f"Embedding generated for document {doc_id}")
            else:
                logger.error(f"Failed to generate embedding for document {doc_id}")
        except Exception as e:
            logger.error(f"Embedding generation failed for document {doc_id}: {e}")
    
    async def ask_question(self, question: str, use_rag: bool = True) -> Dict[str, Any]:
        if not self.initialized:
            await self.initialize()
        
        start_time = time.time()
        result = {
            "success": False,
            "question": question,
            "answer": "",
            "sources": [],
            "rag_used": use_rag,
            "response_time": 0,
            "error": None
        }
        
        try:
            context_docs = []
            search_method = "none"
            
            if use_rag:
                stats = await db_service.get_statistics()
                total_docs = stats.get('documents', 0)
                
                logger.info(f"Database has {total_docs} total documents")
                
                if total_docs == 0:
                    logger.warning("No documents found in database, RAG cannot work")
                    search_method = "no_docs"
                else:
                    vectorized_docs = stats.get('vectorized_documents', 0)
                    
                    if vectorized_docs > 0:
                        try:
                            logger.info(f"Trying vector search for: {question[:100]}...")
                            question_embedding = await ai_service.get_embedding(question)
                            
                            if question_embedding:
                                context_docs = await db_service.search_similar_documents(
                                    question_embedding, 
                                    config.MAX_CONTEXT_CHUNKS
                                )
                                
                                if context_docs:
                                    search_method = "vector"
                                    logger.info(f"Vector search found {len(context_docs)} documents")
                                else:
                                    search_method = "vector_no_match"
                                    logger.info("Vector search returned no matches above threshold")
                        except Exception as vector_error:
                            search_method = "vector_error"
                            logger.error(f"Vector search failed: {vector_error}")
                    
                    if not context_docs:
                        try:
                            logger.info(f"Trying keyword search for: {question[:100]}...")
                            context_docs = await db_service.keyword_search(
                                question, 
                                config.MAX_CONTEXT_CHUNKS
                            )
                            
                            if context_docs:
                                search_method = "keyword"
                                logger.info(f"Keyword search found {len(context_docs)} documents")
                            else:
                                search_method = "keyword_no_match"
                                logger.info("Keyword search returned no matches")
                        except Exception as keyword_error:
                            search_method = "keyword_error"
                            logger.error(f"Keyword search failed: {keyword_error}")
            
            logger.info(f"Final search method: {search_method}, Context docs: {len(context_docs)}")
            
            messages = self.text_processor.build_rag_prompt(question, context_docs)
            logger.info(f"Calling AI with {len(context_docs)} context documents")
            
            answer = await ai_service.chat_completion(messages)
            
            if context_docs:
                result["sources"] = [
                    {
                        "filename": doc.get("filename", "Unknown"),
                        "content": doc["content"][:150] + "..." if len(doc["content"]) > 150 else doc["content"],
                        "similarity": doc.get("similarity", 0),
                        "search_method": search_method
                    }
                    for doc in context_docs
                ]
                result["rag_used"] = True
            else:
                result["rag_used"] = False
            
            result["answer"] = answer
            result["success"] = True
            
            source_filenames = [doc.get("filename", "") for doc in context_docs]
            await db_service.save_query_history(
                question, answer, source_filenames, time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            result["error"] = str(e)
            
            try:
                fallback_answer = await ai_service.chat_completion([
                    {"role": "user", "content": question}
                ])
                result["answer"] = fallback_answer
                result["success"] = True
                result["rag_used"] = False
            except Exception as fallback_error:
                result["answer"] = f"System error: {str(e)}"
        
        result["response_time"] = time.time() - start_time
        return result
    
    async def get_stats(self) -> Dict[str, Any]:
        try:
            stats = await db_service.get_statistics()
            stats.update({
                "ai_service": "Alibaba DashScope",
                "embedding_dimension": config.EMBEDDING_DIM,
                "similarity_threshold": config.SIMILARITY_THRESHOLD,
                "initialized": self.initialized
            })
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

rag_processor = RAGProcessor()