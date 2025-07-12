import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from config.settings import get_settings
from models.schemas import ChatMessage, Session

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseService:
    """MongoDB database service for chat history and session management"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        self.is_connected = False
        self.active_connections: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            mongodb_url = settings.get_mongodb_url()
            self.client = AsyncIOMotorClient(mongodb_url)
            self.database = self.client[settings.mongodb_database]
            
            # Test connection
            await self.client.admin.command('ping')
            self.is_connected = True
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("✅ MongoDB connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ MongoDB connection failed: {e}")
            logger.info("🔄 Running in development mode without MongoDB - some features may be limited")
            self.is_connected = False
            # Don't raise the exception - allow the app to start without MongoDB
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Sessions collection indexes
            await self.database.sessions.create_index("session_id", unique=True)
            await self.database.sessions.create_index("created_at")
            await self.database.sessions.create_index("last_activity")
            
            # Messages collection indexes
            await self.database.messages.create_index([("session_id", 1), ("timestamp", 1)])
            await self.database.messages.create_index("timestamp")
            
            # Query history indexes
            await self.database.query_history.create_index([("session_id", 1), ("timestamp", 1)])
            await self.database.query_history.create_index("query_hash")
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("🛑 MongoDB connection closed")
    
    async def test_connection(self, connection_params: Dict[str, Any]) -> bool:
        """Test database connection with given parameters"""
        try:
            # This would implement actual database connection testing
            # For now, we'll simulate a successful connection
            db_type = connection_params.get("type", "").lower()
            
            if db_type in ["postgresql", "mysql", "sqlite"]:
                # Simulate connection test
                await asyncio.sleep(1)  # Simulate connection time
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False
    
    async def create_session(self, session_id: str, user_id: Optional[str] = None) -> Session:
        """Create a new chat session"""
        try:
            session_data = {
                "session_id": session_id,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "user_id": user_id,
                "data_source": None,
                "message_count": 0,
                "metadata": {}
            }
            
            await self.database.sessions.insert_one(session_data)
            
            return Session(**session_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            session_data = await self.database.sessions.find_one({"session_id": session_id})
            
            if session_data:
                # Remove MongoDB ObjectId for serialization
                session_data.pop("_id", None)
                return Session(**session_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get session: {e}")
            return None
    
    async def update_session_activity(self, session_id: str, data_source: Optional[Dict] = None):
        """Update session last activity and data source"""
        try:
            update_data = {"last_activity": datetime.utcnow()}
            
            if data_source:
                update_data["data_source"] = data_source
            
            await self.database.sessions.update_one(
                {"session_id": session_id},
                {"$set": update_data}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to update session activity: {e}")
    
    async def save_message(self, session_id: str, message: ChatMessage):
        """Save chat message to database"""
        try:
            message_data = {
                "session_id": session_id,
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp,
                "metadata": message.metadata or {}
            }
            
            await self.database.messages.insert_one(message_data)
            
            # Update session message count
            await self.database.sessions.update_one(
                {"session_id": session_id},
                {"$inc": {"message_count": 1}}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to save message: {e}")
            raise
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        try:
            cursor = self.database.messages.find(
                {"session_id": session_id}
            ).sort("timestamp", 1).limit(limit)
            
            messages = []
            async for doc in cursor:
                doc.pop("_id", None)  # Remove ObjectId
                messages.append(doc)
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Failed to get chat history: {e}")
            return []
    
    async def clear_chat_history(self, session_id: str):
        """Clear chat history for a session"""
        try:
            await self.database.messages.delete_many({"session_id": session_id})
            
            # Reset session message count
            await self.database.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"message_count": 0}}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to clear chat history: {e}")
            raise
    
    async def save_query_execution(self, session_id: str, query: str, results: Any, execution_time: float):
        """Save query execution details"""
        try:
            query_data = {
                "session_id": session_id,
                "query": query,
                "query_hash": hash(query),
                "execution_time": execution_time,
                "result_count": len(results) if isinstance(results, list) else 1,
                "timestamp": datetime.utcnow(),
                "status": "success"
            }
            
            await self.database.query_history.insert_one(query_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to save query execution: {e}")
    
    async def get_session_count(self) -> int:
        """Get total number of sessions"""
        try:
            return await self.database.sessions.count_documents({})
        except Exception as e:
            logger.error(f"❌ Failed to get session count: {e}")
            return 0
    
    async def get_query_count(self) -> int:
        """Get total number of queries executed"""
        try:
            return await self.database.query_history.count_documents({})
        except Exception as e:
            logger.error(f"❌ Failed to get query count: {e}")
            return 0
    
    async def get_active_sessions(self, hours: int = 24) -> List[Session]:
        """Get active sessions within specified hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            cursor = self.database.sessions.find(
                {"last_activity": {"$gte": cutoff_time}}
            ).sort("last_activity", -1)
            
            sessions = []
            async for doc in cursor:
                doc.pop("_id", None)
                sessions.append(Session(**doc))
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to get active sessions: {e}")
            return []
    
    async def cleanup_old_sessions(self, days: int = 30):
        """Clean up old sessions and messages"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Get sessions to delete
            sessions_to_delete = []
            cursor = self.database.sessions.find(
                {"last_activity": {"$lt": cutoff_time}},
                {"session_id": 1}
            )
            
            async for doc in cursor:
                sessions_to_delete.append(doc["session_id"])
            
            if sessions_to_delete:
                # Delete messages for old sessions
                await self.database.messages.delete_many(
                    {"session_id": {"$in": sessions_to_delete}}
                )
                
                # Delete old sessions
                await self.database.sessions.delete_many(
                    {"session_id": {"$in": sessions_to_delete}}
                )
                
                # Delete old query history
                await self.database.query_history.delete_many(
                    {"session_id": {"$in": sessions_to_delete}}
                )
                
                logger.info(f"🧹 Cleaned up {len(sessions_to_delete)} old sessions")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old sessions: {e}")
    
    async def execute_query(self, query: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL query on external database"""
        try:
            # This would implement actual query execution against external databases
            # For now, we'll return a mock result
            
            execution_start = datetime.utcnow()
            
            # Simulate query execution
            await asyncio.sleep(0.5)
            
            # Mock results
            mock_results = [
                {"id": 1, "name": "Sample Data", "value": 100},
                {"id": 2, "name": "Test Record", "value": 200}
            ]
            
            execution_time = (datetime.utcnow() - execution_start).total_seconds()
            
            return {
                "results": mock_results,
                "execution_time": execution_time,
                "row_count": len(mock_results),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise
