from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class VectorService:
    """Qdrant vector database service for semantic search"""
    
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.encoder = None
        self.is_connected = False
        self.collection_name = settings.qdrant_collection_name
        self.vector_size = settings.qdrant_vector_size
        
    async def initialize(self):
        """Initialize Qdrant client and sentence transformer"""
        try:
            # Initialize Qdrant client with version check disabled
            self.client = AsyncQdrantClient(
                url=settings.qdrant_url,
                check_compatibility=False
            )
            
            # Initialize sentence transformer for embeddings
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            self.vector_size = self.encoder.get_sentence_embedding_dimension()
            
            # Test connection
            await self.client.get_collections()
            self.is_connected = True
            
            # Create default collection if it doesn't exist
            await self._ensure_collection_exists(self.collection_name)
            
            logger.info("✅ Qdrant connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ Qdrant connection failed: {e}")
            logger.info("🔄 Running in development mode without Qdrant - vector search features disabled")
            self.is_connected = False
            # Don't raise the exception - allow the app to start without Qdrant
    
    async def close(self):
        """Close Qdrant connection"""
        if self.client:
            await self.client.close()
            self.is_connected = False
            logger.info("🛑 Qdrant connection closed")
    
    async def _ensure_collection_exists(self, collection_name: str):
        """Ensure collection exists, create if not"""
        try:
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create collection: {e}")
            raise
    
    def _encode_text(self, text: str) -> List[float]:
        """Encode text to vector embedding"""
        try:
            if self.encoder is None:
                raise ValueError("Encoder not initialized")
            
            # Generate embedding
            embedding = self.encoder.encode(text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"❌ Failed to encode text: {e}")
            raise
    
    async def store_document(self, 
                           text: str, 
                           metadata: Dict[str, Any],
                           collection_name: Optional[str] = None) -> str:
        """Store document in vector database"""
        try:
            if not self.is_connected:
                raise ValueError("Vector service not connected")
            
            collection = collection_name or self.collection_name
            await self._ensure_collection_exists(collection)
            
            # Generate embedding
            vector = self._encode_text(text)
            
            # Create unique ID
            doc_id = str(uuid.uuid4())
            
            # Prepare point
            point = PointStruct(
                id=doc_id,
                vector=vector,
                payload={
                    "text": text,
                    "timestamp": datetime.utcnow().isoformat(),
                    **metadata
                }
            )
            
            # Store in Qdrant
            await self.client.upsert(
                collection_name=collection,
                points=[point]
            )
            
            logger.info(f"✅ Stored document with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store document: {e}")
            raise
    
    async def store_data_schema(self, 
                              schema_info: Dict[str, Any],
                              collection_name: Optional[str] = None) -> str:
        """Store data schema information for later retrieval"""
        try:
            schema_text = self._schema_to_text(schema_info)
            
            metadata = {
                "type": "schema",
                "source": schema_info.get("source", "unknown"),
                "table_count": len(schema_info.get("tables", [])),
                "schema_info": schema_info
            }
            
            return await self.store_document(
                text=schema_text,
                metadata=metadata,
                collection_name=collection_name
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to store schema: {e}")
            raise
    
    def _schema_to_text(self, schema_info: Dict[str, Any]) -> str:
        """Convert schema information to searchable text"""
        text_parts = []
        
        if "tables" in schema_info:
            for table in schema_info["tables"]:
                table_name = table.get("name", "")
                text_parts.append(f"Table: {table_name}")
                
                if "columns" in table:
                    for column in table["columns"]:
                        col_name = column.get("name", "")
                        col_type = column.get("type", "")
                        text_parts.append(f"Column: {col_name} Type: {col_type}")
        
        return " ".join(text_parts)
    
    async def search(self, 
                    query: str,
                    collection_name: Optional[str] = None,
                    limit: int = 10,
                    score_threshold: float = 0.7,
                    filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform semantic search"""
        try:
            if not self.is_connected:
                raise ValueError("Vector service not connected")
            
            collection = collection_name or self.collection_name
            
            # Generate query embedding
            query_vector = self._encode_text(query)
            
            # Prepare filter if provided
            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=conditions)
            
            # Perform search
            search_results = await self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
                with_payload=True
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": {k: v for k, v in result.payload.items() if k != "text"}
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    async def search_similar_queries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar queries in chat history"""
        try:
            filters = {"type": "query"}
            return await self.search(
                query=query,
                limit=limit,
                filters=filters,
                score_threshold=0.8
            )
            
        except Exception as e:
            logger.error(f"❌ Similar query search failed: {e}")
            return []
    
    async def search_schema_info(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant schema information"""
        try:
            filters = {"type": "schema"}
            return await self.search(
                query=query,
                limit=limit,
                filters=filters,
                score_threshold=0.6
            )
            
        except Exception as e:
            logger.error(f"❌ Schema search failed: {e}")
            return []
    
    async def store_query_result(self, 
                                query: str, 
                                result_summary: str,
                                session_id: str) -> str:
        """Store query and result for future similarity search"""
        try:
            text = f"Query: {query} Result: {result_summary}"
            
            metadata = {
                "type": "query",
                "session_id": session_id,
                "query": query,
                "result_summary": result_summary
            }
            
            return await self.store_document(text=text, metadata=metadata)
            
        except Exception as e:
            logger.error(f"❌ Failed to store query result: {e}")
            raise
    
    async def delete_document(self, doc_id: str, collection_name: Optional[str] = None) -> bool:
        """Delete document by ID"""
        try:
            collection = collection_name or self.collection_name
            
            await self.client.delete(
                collection_name=collection,
                points_selector=[doc_id]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document: {e}")
            return False
    
    async def get_collection_count(self) -> int:
        """Get number of collections"""
        try:
            if not self.is_connected:
                return 0
            
            collections = await self.client.get_collections()
            return len(collections.collections)
            
        except Exception as e:
            logger.error(f"❌ Failed to get collection count: {e}")
            return 0
    
    async def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Get collection information"""
        try:
            collection = collection_name or self.collection_name
            
            info = await self.client.get_collection(collection_name=collection)
            
            return {
                "name": collection,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status.value if info.status else "unknown"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get collection info: {e}")
            return {}
    
    async def clear_collection(self, collection_name: Optional[str] = None) -> bool:
        """Clear all points from collection"""
        try:
            collection = collection_name or self.collection_name
            
            await self.client.delete(
                collection_name=collection,
                points_selector=Filter()  # Delete all points
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear collection: {e}")
            return False
