from typing import Optional, Dict, Any
import os
from functools import wraps
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from config.settings import get_settings

class LangfuseService:
    """Service for LLM observability and analytics with Langfuse"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Langfuse] = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize Langfuse client if enabled and configured"""
        if not self.settings.langfuse_enabled:
            return False
            
        if not self.settings.langfuse_public_key or not self.settings.langfuse_secret_key:
            print("Warning: Langfuse enabled but missing API keys")
            return False
            
        try:
            langfuse_host = self.settings.get_langfuse_host()
            self._client = Langfuse(
                public_key=self.settings.langfuse_public_key,
                secret_key=self.settings.langfuse_secret_key,
                host=langfuse_host,
                debug=self.settings.langfuse_debug,
                flush_at=self.settings.langfuse_flush_at,
                flush_interval=self.settings.langfuse_flush_interval,
                max_retries=self.settings.langfuse_max_retries,
            )
            self._initialized = True
            print(f"✅ Langfuse initialized successfully - Host: {langfuse_host}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Langfuse: {str(e)}")
            return False
    
    @property
    def client(self) -> Optional[Langfuse]:
        """Get Langfuse client instance"""
        if not self._initialized:
            self.initialize()
        return self._client
    
    @property
    def is_enabled(self) -> bool:
        """Check if Langfuse is enabled and initialized"""
        return self._initialized and self._client is not None
    
    def create_trace(self, name: str, **kwargs) -> Optional[Any]:
        """Create a new trace"""
        if not self.is_enabled:
            return None
            
        try:
            return self._client.trace(name=name, **kwargs)
        except Exception as e:
            print(f"Failed to create Langfuse trace: {str(e)}")
            return None
    
    def create_span(self, name: str, trace_id: Optional[str] = None, **kwargs) -> Optional[Any]:
        """Create a new span"""
        if not self.is_enabled:
            return None
            
        try:
            if trace_id:
                return self._client.span(name=name, trace_id=trace_id, **kwargs)
            else:
                return self._client.span(name=name, **kwargs)
        except Exception as e:
            print(f"Failed to create Langfuse span: {str(e)}")
            return None
    
    def log_generation(self, 
                      name: str,
                      model: str,
                      input_data: Dict[str, Any],
                      output_data: Dict[str, Any],
                      **kwargs) -> Optional[Any]:
        """Log an LLM generation"""
        if not self.is_enabled:
            return None
            
        try:
            return self._client.generation(
                name=name,
                model=model,
                input=input_data,
                output=output_data,
                **kwargs
            )
        except Exception as e:
            print(f"Failed to log Langfuse generation: {str(e)}")
            return None
    
    def log_score(self, trace_id: str, name: str, value: float, **kwargs) -> Optional[Any]:
        """Log a score for a trace"""
        if not self.is_enabled:
            return None
            
        try:
            return self._client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                **kwargs
            )
        except Exception as e:
            print(f"Failed to log Langfuse score: {str(e)}")
            return None
    
    def flush(self):
        """Flush pending events"""
        if self.is_enabled:
            try:
                self._client.flush()
            except Exception as e:
                print(f"Failed to flush Langfuse events: {str(e)}")

# Global instance
_langfuse_service: Optional[LangfuseService] = None

def get_langfuse_service() -> LangfuseService:
    """Get the global Langfuse service instance"""
    global _langfuse_service
    if _langfuse_service is None:
        _langfuse_service = LangfuseService()
    return _langfuse_service

def langfuse_observe(name: Optional[str] = None):
    """Decorator to observe function calls with Langfuse"""
    def decorator(func):
        # Only apply Langfuse decorator if enabled
        service = get_langfuse_service()
        if service.settings.langfuse_enabled:
            return observe(name=name or func.__name__)(func)
        else:
            # Return original function if Langfuse is disabled
            return func
    return decorator

# Example usage functions
def track_agent_execution(agent_name: str, input_data: Dict[str, Any], output_data: Dict[str, Any]):
    """Track CrewAI agent execution"""
    service = get_langfuse_service()
    if service.is_enabled:
        service.log_generation(
            name=f"agent_{agent_name}",
            model="crewai",
            input_data=input_data,
            output_data=output_data,
            metadata={"agent_type": "crewai", "agent_name": agent_name}
        )

def track_langgraph_workflow(workflow_name: str, input_data: Dict[str, Any], output_data: Dict[str, Any]):
    """Track LangGraph workflow execution"""
    service = get_langfuse_service()
    if service.is_enabled:
        service.log_generation(
            name=f"workflow_{workflow_name}",
            model="langgraph", 
            input_data=input_data,
            output_data=output_data,
            metadata={"workflow_type": "langgraph", "workflow_name": workflow_name}
        )

def track_sql_query(query: str, result: Dict[str, Any]):
    """Track SQL query execution"""
    service = get_langfuse_service()
    if service.is_enabled:
        service.log_generation(
            name="sql_query",
            model="sql_agent",
            input_data={"query": query},
            output_data=result,
            metadata={"query_type": "sql"}
        )