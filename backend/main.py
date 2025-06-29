from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import os
from typing import Dict, List, Optional, Any
import json
import pandas as pd
from datetime import datetime
import uvicorn

# Local imports
from models.schemas import (
    ChatRequest, 
    ChatResponse, 
    DatabaseConnection, 
    FileUploadResponse,
    HealthResponse
)
from services.database_service import DatabaseService
from services.chat_service import ChatService
from services.file_service import FileService
from services.vector_service import VectorService
from agents.langgraph_orchestrator import LangGraphOrchestrator
from agents.crew_agent import CrewDataAgent
from agents.sql_agent import SQLAgent
from config.settings import get_settings
from services.langfuse_service import get_langfuse_service

# Configuration
settings = get_settings()

# Global services
database_service: DatabaseService = None
chat_service: ChatService = None
file_service: FileService = None
vector_service: VectorService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global database_service, chat_service, file_service, vector_service
    
    # Initialize services
    print("🚀 Starting Chat with Data Backend...")
    
    try:
        # Initialize core services
        database_service = DatabaseService()
        await database_service.initialize()
        
        vector_service = VectorService()
        await vector_service.initialize()
        
        file_service = FileService()
        
        chat_service = ChatService(
            database_service=database_service,
            vector_service=vector_service,
            file_service=file_service
        )
        
        # Initialize Langfuse for LLM observability
        langfuse_service = get_langfuse_service()
        if langfuse_service.initialize():
            print("✅ Langfuse observability initialized")
        else:
            print("ℹ️ Langfuse observability disabled (not configured)")
        
        print("✅ All services initialized successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise
    
    yield
    
    # Cleanup
    print("🛑 Shutting down services...")
    
    # Flush Langfuse events
    langfuse_service = get_langfuse_service()
    if langfuse_service.is_enabled:
        langfuse_service.flush()
        print("✅ Langfuse events flushed")
    
    if database_service:
        await database_service.close()
    if vector_service:
        await vector_service.close()

# Create FastAPI app
app = FastAPI(
    title="Chat with Data API",
    description="Backend API for intelligent data analysis conversations with LangGraph and CrewAI",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        services={
            "database": "connected" if database_service and database_service.is_connected else "disconnected",
            "vector_store": "connected" if vector_service and vector_service.is_connected else "disconnected",
            "file_service": "active",
            "chat_service": "active"
        }
    )

# File upload endpoint
@app.post("/upload-file", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload and process data file"""
    try:
        if not file_service:
            raise HTTPException(status_code=500, detail="File service not initialized")
        
        # Process uploaded file
        result = await file_service.process_uploaded_file(file)
        
        return FileUploadResponse(
            filename=result["filename"],
            file_type=result["file_type"],
            rows=result.get("rows", 0),
            columns=result.get("columns", 0),
            preview=result.get("preview", []),
            file_id=result["file_id"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File upload failed: {str(e)}")

# Database connection endpoint
@app.post("/connect-database")
async def connect_database(connection: DatabaseConnection):
    """Test and establish database connection"""
    try:
        if not database_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        success = await database_service.test_connection(connection.dict())
        
        if success:
            return {"status": "connected", "message": "Database connection successful"}
        else:
            raise HTTPException(status_code=400, detail="Database connection failed")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection error: {str(e)}")

# Sample data loading endpoint
@app.post("/load-sample-data")
async def load_sample_data(request: Dict[str, str]):
    """Load sample dataset"""
    try:
        if not file_service:
            raise HTTPException(status_code=500, detail="File service not initialized")
        
        dataset_name = request.get("dataset")
        result = await file_service.load_sample_dataset(dataset_name)
        
        return {
            "dataset": dataset_name,
            "rows": result.get("rows", 0),
            "columns": result.get("columns", 0),
            "preview": result.get("preview", []),
            "file_id": result["file_id"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load sample data: {str(e)}")

# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for data analysis"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="Chat service not initialized")
        
        # Process chat request
        response = await chat_service.process_chat_message(
            message=request.message,
            session_id=request.session_id,
            data_source=request.data_source
        )
        
        return ChatResponse(
            message=response["message"],
            data=response.get("data"),
            query_executed=response.get("query_executed"),
            execution_time=response.get("execution_time", 0),
            suggestions=response.get("suggestions", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

# Chat history endpoints
@app.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        if not database_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        history = await database_service.get_chat_history(session_id)
        return {"session_id": session_id, "messages": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")

@app.delete("/chat-history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    try:
        if not database_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        await database_service.clear_chat_history(session_id)
        return {"message": "Chat history cleared successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")

# Data analysis endpoints
@app.post("/analyze-data")
async def analyze_data(request: Dict[str, Any]):
    """Perform enhanced data analysis using PandasAI v3 semantic layer"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="Chat service not initialized")
        
        # Enhanced analysis with PandasAI v3 semantic layer
        analysis_result = await chat_service.analyze_data_with_pandas_ai(
            data_source=request.get("data_source"),
            query=request.get("query"),
            analysis_type=request.get("analysis_type", "general")
        )
        
        # Add metadata about the analysis method used
        if "message" in analysis_result:
            version_info = " (Enhanced with PandasAI v3 semantic layer)" if settings.pandasai_version == "3.0" else " (PandasAI v1.5)"
            analysis_result["analysis_method"] = version_info
            analysis_result["semantic_layer_enabled"] = settings.enable_semantic_layer
        
        return analysis_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced data analysis failed: {str(e)}")

# SQL query endpoints
@app.post("/execute-sql")
async def execute_sql_query(request: Dict[str, Any]):
    """Execute SQL query on connected database"""
    try:
        if not database_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        result = await database_service.execute_query(
            query=request.get("query"),
            connection_params=request.get("connection_params")
        )
        
        return {
            "results": result,
            "query": request.get("query"),
            "execution_time": result.get("execution_time", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL execution failed: {str(e)}")

# Vector search endpoints
@app.post("/semantic-search")
async def semantic_search(request: Dict[str, Any]):
    """Perform semantic search on vector database"""
    try:
        if not vector_service:
            raise HTTPException(status_code=500, detail="Vector service not initialized")
        
        results = await vector_service.search(
            query=request.get("query"),
            collection_name=request.get("collection", "default"),
            limit=request.get("limit", 10)
        )
        
        return {"results": results, "query": request.get("query")}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

# System metrics endpoint
@app.get("/metrics")
async def get_system_metrics():
    """Get system metrics and statistics"""
    try:
        metrics = {
            "total_sessions": await database_service.get_session_count() if database_service else 0,
            "total_queries": await database_service.get_query_count() if database_service else 0,
            "active_connections": len(database_service.active_connections) if database_service else 0,
            "vector_collections": await vector_service.get_collection_count() if vector_service else 0,
            "uptime": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        return metrics
        
    except Exception as e:
        return {"error": f"Failed to get metrics: {str(e)}"}

# WebSocket endpoint for real-time chat (optional enhancement)
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message
            if chat_service:
                response = await chat_service.process_chat_message(
                    message=message_data.get("message"),
                    session_id=session_id,
                    data_source=message_data.get("data_source")
                )
                
                # Send response back
                await websocket.send_text(json.dumps(response))
            else:
                await websocket.send_text(json.dumps({"error": "Chat service not available"}))
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 