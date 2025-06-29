import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from services.database_service import DatabaseService
from services.vector_service import VectorService
from services.file_service import FileService
from agents.sql_agent import SQLAgent
from agents.crew_agent import CrewDataAgent
from agents.langgraph_orchestrator import LangGraphOrchestrator
from models.schemas import ChatMessage
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ChatService:
    """Main chat service that orchestrates all agents and services"""
    
    def __init__(self, 
                 database_service: DatabaseService,
                 vector_service: VectorService,
                 file_service: FileService):
        self.database_service = database_service
        self.vector_service = vector_service
        self.file_service = file_service
        
        # Initialize agents
        self.sql_agent = SQLAgent()
        self.crew_agent = CrewDataAgent()
        self.langgraph_orchestrator = LangGraphOrchestrator(
            crew_agent=self.crew_agent,
            sql_agent=self.sql_agent
        )
        
        # Query intent classification patterns
        self.intent_patterns = {
            "data_analysis": ["analyze", "summary", "statistics", "describe", "overview"],
            "visualization": ["chart", "plot", "graph", "visualize", "show"],
            "sql_query": ["select", "from", "where", "join", "database", "table"],
            "comparison": ["compare", "difference", "versus", "vs", "between"],
            "trend": ["trend", "over time", "timeline", "growth", "change"],
            "filter": ["filter", "subset", "only", "exclude", "include"],
            "aggregation": ["sum", "count", "average", "mean", "total", "group"]
        }
    
    async def process_chat_message(self, 
                                 message: str,
                                 session_id: str,
                                 data_source: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process incoming chat message and return response"""
        try:
            start_time = datetime.utcnow()
            
            # Ensure session exists
            session = await self.database_service.get_session(session_id)
            if not session:
                session = await self.database_service.create_session(session_id)
            
            # Update session activity
            await self.database_service.update_session_activity(session_id, data_source)
            
            # Save user message
            user_message = ChatMessage(role="user", content=message)
            await self.database_service.save_message(session_id, user_message)
            
            # Get chat history for context
            chat_history = await self.database_service.get_chat_history(session_id, limit=10)
            
            # Classify intent
            intent = self._classify_intent(message)
            
            # Search for similar queries
            similar_queries = await self.vector_service.search_similar_queries(message)
            
            # Process message based on data source and intent
            if data_source:
                response = await self._process_with_data_source(
                    message=message,
                    intent=intent,
                    data_source=data_source,
                    chat_history=chat_history,
                    similar_queries=similar_queries
                )
            else:
                response = await self._process_without_data_source(message, intent)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            response["execution_time"] = execution_time
            
            # Save assistant message
            assistant_message = ChatMessage(
                role="assistant", 
                content=response["message"],
                metadata={"intent": intent, "execution_time": execution_time}
            )
            await self.database_service.save_message(session_id, assistant_message)
            
            # Store query in vector database for future similarity search
            if data_source and response.get("data"):
                await self.vector_service.store_query_result(
                    query=message,
                    result_summary=self._summarize_result(response),
                    session_id=session_id
                )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Chat processing failed: {e}")
            return {
                "message": "I apologize, but I encountered an error processing your request. Please try again.",
                "error": str(e)
            }
    
    def _classify_intent(self, message: str) -> str:
        """Classify user intent based on message content"""
        message_lower = message.lower()
        
        # Score each intent
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return highest scoring intent
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        else:
            return "general"
    
    async def _process_with_data_source(self,
                                      message: str,
                                      intent: str,
                                      data_source: Dict[str, Any],
                                      chat_history: List[Dict[str, Any]],
                                      similar_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process message with connected data source"""
        try:
            # Determine processing strategy based on data source type
            if "file_id" in data_source:
                return await self._process_file_query(message, intent, data_source, chat_history)
            elif "type" in data_source and data_source["type"] in ["postgresql", "mysql", "sqlite"]:
                return await self._process_database_query(message, intent, data_source, chat_history)
            else:
                return await self._process_general_data_query(message, intent, data_source)
                
        except Exception as e:
            logger.error(f"❌ Data source processing failed: {e}")
            return {
                "message": f"I encountered an error processing your query: {str(e)}",
                "suggestions": ["Try rephrasing your question", "Check your data source connection"]
            }
    
    async def _process_file_query(self,
                                message: str,
                                intent: str,
                                data_source: Dict[str, Any],
                                chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process query against uploaded file"""
        try:
            file_id = data_source.get("file_id")
            if not file_id:
                return {"message": "No file ID provided in data source."}
            
            # Get file data
            df = await self.file_service.get_file_data(file_id)
            if df is None:
                return {"message": "Could not load the specified file."}
            
            # Use LangGraph orchestrator to route to appropriate agents
            return await self.langgraph_orchestrator.process_query(
                query=message,
                data_source={"file_data": df, "file_id": file_id},
                chat_history=chat_history,
                intent=intent
            )
                
        except Exception as e:
            logger.error(f"❌ File query processing failed: {e}")
            return {"message": f"Error processing file query: {str(e)}"}
    
    async def _process_database_query(self,
                                    message: str,
                                    intent: str,
                                    data_source: Dict[str, Any],
                                    chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process query against database connection"""
        try:
            # Get schema information from vector store
            schema_info = await self.vector_service.search_schema_info(message)
            
            # Generate SQL query
            sql_query = await self.sql_agent.generate_sql_query(
                message=message,
                schema_info=schema_info,
                chat_history=chat_history
            )
            
            if not sql_query:
                return {"message": "I couldn't generate a SQL query for your request."}
            
            # Execute query
            query_result = await self.database_service.execute_query(
                query=sql_query,
                connection_params=data_source
            )
            
            # Format response
            return {
                "message": f"I executed your query and found {query_result.get('row_count', 0)} results.",
                "data": {
                    "table": query_result.get("results", []),
                    "query": sql_query
                },
                "query_executed": sql_query,
                "suggestions": self._generate_follow_up_suggestions(intent, query_result)
            }
            
        except Exception as e:
            logger.error(f"❌ Database query processing failed: {e}")
            return {"message": f"Error executing database query: {str(e)}"}
    
    async def _process_general_data_query(self,
                                        message: str,
                                        intent: str,
                                        data_source: Dict[str, Any]) -> Dict[str, Any]:
        """Process general data query"""
        return await self.crew_agent.process_general_query(message, data_source, intent)
    
    async def _process_without_data_source(self, message: str, intent: str) -> Dict[str, Any]:
        """Process message without data source"""
        return {
            "message": "I'd be happy to help you analyze your data! Please upload a file or connect to a database first.",
            "suggestions": [
                "Upload a CSV or Excel file",
                "Connect to a database",
                "Try one of our sample datasets"
            ]
        }
    
    async def analyze_data_with_pandas_ai(self,
                                        data_source: Dict[str, Any],
                                        query: str,
                                        analysis_type: str = "general") -> Dict[str, Any]:
        """Analyze data using CrewAI and LangGraph orchestration"""
        try:
            if "file_id" not in data_source:
                return {"error": "No file ID provided"}
            
            df = await self.file_service.get_file_data(data_source["file_id"])
            if df is None:
                return {"error": "Could not load file data"}
            
            # Use LangGraph orchestrator with CrewAI agents
            logger.info("🤖 Using CrewAI + LangGraph for data analysis")
            return await self.langgraph_orchestrator.process_query(
                query=query,
                data_source={"file_data": df, "file_id": data_source["file_id"]},
                chat_history=[],
                intent=analysis_type
            )
            
        except Exception as e:
            logger.error(f"❌ Data analysis failed: {e}")
            return {"error": str(e)}
    
    def _summarize_result(self, response: Dict[str, Any]) -> str:
        """Create a summary of the response for vector storage"""
        summary_parts = []
        
        if response.get("message"):
            summary_parts.append(response["message"][:200])
        
        if response.get("data", {}).get("table"):
            table_data = response["data"]["table"]
            summary_parts.append(f"Returned {len(table_data)} rows of data")
        
        if response.get("query_executed"):
            summary_parts.append(f"Executed: {response['query_executed'][:100]}")
        
        return " | ".join(summary_parts)
    
    def _generate_follow_up_suggestions(self, intent: str, query_result: Dict[str, Any]) -> List[str]:
        """Generate follow-up suggestions based on intent and results"""
        suggestions = []
        
        if intent == "data_analysis":
            suggestions.extend([
                "Show me a visualization of this data",
                "Can you summarize the key insights?",
                "What are the trends in this data?"
            ])
        elif intent == "visualization":
            suggestions.extend([
                "Create a different type of chart",
                "Show me the data behind this chart",
                "Compare with another metric"
            ])
        elif intent in ["sql_query", "filter"]:
            suggestions.extend([
                "Show me more details about these results",
                "Apply additional filters",
                "Export this data"
            ])
        
        # Add generic suggestions
        suggestions.extend([
            "Analyze a different aspect of the data",
            "Show me similar data patterns"
        ])
        
        return suggestions[:3]  # Return top 3 suggestions 