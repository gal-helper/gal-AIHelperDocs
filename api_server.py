from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import tempfile
import os
from typing import List, Dict, Any
import asyncio
from rag_processor import rag_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI RAG API",
    description="API for AI RAG Question Answering System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI RAG API server...")
    await rag_processor.initialize()
    logger.info("Services initialized successfully")

@app.get("/")
async def root():
    return {
        "message": "AI RAG API Server",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/ask": "Ask a question (POST)",
            "/upload": "Upload document (POST)",
            "/stats": "Get system statistics",
            "/history": "Get query history"
        }
    }

@app.get("/health")
async def health_check():
    stats = await rag_processor.get_stats()
    return {
        "status": "healthy",
        "services": {
            "ai": "operational",
            "database": "operational" if "error" not in stats else "error",
            "rag_processor": "operational"
        }
    }

@app.post("/ask")
async def ask_question(
    question: str = Form(...),
    use_rag: bool = Form(True)
):
    try:
        logger.info(f"Processing question: {question[:100]}...")
        
        result = await rag_processor.ask_question(question, use_rag)
        
        response = {
            "success": result["success"],
            "question": question,
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "rag_used": use_rag,
            "response_time": result.get("response_time", 0)
        }
        
        if result.get("error"):
            response["error"] = result["error"]
        
        return response
    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        logger.info(f"Uploading file: {file.filename}")

        result = await rag_processor.process_document(tmp_path)

        os.unlink(tmp_path)
        
        response = {
            "filename": file.filename,
            "success": result["success"],
            "chunks": result.get("chunks", 0),
            "documents_processed": result.get("documents_processed", 0),
            "message": result.get("message", "")
        }
        
        if result.get("document_ids"):
            response["document_ids"] = result["document_ids"]
        
        return response
    except Exception as e:
        logger.error(f"Error in /upload endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_statistics():
    try:
        stats = await rag_processor.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error in /stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 10):
    try:
        stats = await rag_processor.get_stats()
        history = stats.get("recent_queries", [])
        return {
            "count": len(history),
            "queries": history[:limit]
        }
    except Exception as e:
        logger.error(f"Error in /history endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )