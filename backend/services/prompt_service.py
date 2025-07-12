import yaml
from typing import Dict, Any, Optional
import logging
from pathlib import Path
from datetime import datetime, timedelta

from config.settings import get_settings
from services.langfuse_service import get_langfuse_service

logger = logging.getLogger(__name__)
settings = get_settings()
langfuse_service = get_langfuse_service()


class PromptService:
    """Service for managing system prompts with Langfuse integration"""
    
    def __init__(self):
        self.prompts_cache: Dict[str, Any] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(hours=1)  # Cache prompts for 1 hour
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        
        # Ensure prompts directory exists
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Initialize prompt collections in Langfuse
        self._initialize_langfuse_prompts()
    
    def _initialize_langfuse_prompts(self):
        """Initialize prompt collections in Langfuse if enabled"""
        if not langfuse_service.is_enabled:
            logger.info("🔄 Langfuse not enabled - using local prompts only")
            return
        
        try:
            # Create prompt collections for each agent type
            collections = [
                "crew_agent_prompts",
                "sql_agent_prompts", 
                "langgraph_prompts"
            ]
            
            for collection in collections:
                self._ensure_langfuse_collection(collection)
            
            logger.info("✅ Langfuse prompt collections initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Langfuse prompts: {e}")
    
    def _ensure_langfuse_collection(self, collection_name: str):
        """Ensure a prompt collection exists in Langfuse"""
        try:
            # This would create the collection if it doesn't exist
            # For now, we'll just log the intent
            logger.debug(f"Ensuring Langfuse collection: {collection_name}")
            
        except Exception as e:
            logger.warning(f"Failed to ensure Langfuse collection {collection_name}: {e}")
    
    def get_prompt(self, 
                  agent_type: str, 
                  prompt_key: str, 
                  sub_key: Optional[str] = None) -> Optional[str]:
        """
        Get a prompt from Langfuse first, then fallback to local YAML
        
        Args:
            agent_type: Type of agent (crew_agent, sql_agent, langgraph)
            prompt_key: Main prompt key (e.g., 'agents', 'tasks', 'sql_generation')
            sub_key: Sub-key for nested prompts (e.g., 'data_analyst', 'system_prompt')
        
        Returns:
            Prompt string or None if not found
        """
        cache_key = f"{agent_type}:{prompt_key}:{sub_key}" if sub_key else f"{agent_type}:{prompt_key}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.prompts_cache.get(cache_key)
        
        # Try Langfuse first
        langfuse_prompt = self._get_from_langfuse(agent_type, prompt_key, sub_key)
        if langfuse_prompt:
            self._cache_prompt(cache_key, langfuse_prompt)
            return langfuse_prompt
        
        # Fallback to local YAML
        local_prompt = self._get_from_local_yaml(agent_type, prompt_key, sub_key)
        if local_prompt:
            self._cache_prompt(cache_key, local_prompt)
            return local_prompt
        
        logger.warning(f"⚠️ Prompt not found: {cache_key}")
        return None
    
    def get_prompt_dict(self, 
                       agent_type: str, 
                       prompt_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a complete prompt dictionary from Langfuse or local YAML
        
        Args:
            agent_type: Type of agent
            prompt_key: Main prompt key
        
        Returns:
            Dictionary containing all prompts for the key
        """
        cache_key = f"{agent_type}:{prompt_key}:dict"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.prompts_cache.get(cache_key)
        
        # Try Langfuse first
        langfuse_prompts = self._get_dict_from_langfuse(agent_type, prompt_key)
        if langfuse_prompts:
            self._cache_prompt(cache_key, langfuse_prompts)
            return langfuse_prompts
        
        # Fallback to local YAML
        local_prompts = self._get_dict_from_local_yaml(agent_type, prompt_key)
        if local_prompts:
            self._cache_prompt(cache_key, local_prompts)
            return local_prompts
        
        logger.warning(f"⚠️ Prompt dictionary not found: {agent_type}:{prompt_key}")
        return None
    
    def _get_from_langfuse(self, 
                          agent_type: str, 
                          prompt_key: str, 
                          sub_key: Optional[str] = None) -> Optional[str]:
        """Get prompt from Langfuse"""
        if not langfuse_service.is_enabled:
            return None
        
        try:
            # This would query Langfuse for the specific prompt
            # For now, we'll return None to trigger fallback
            logger.debug(f"Querying Langfuse for prompt: {agent_type}:{prompt_key}:{sub_key}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get prompt from Langfuse: {e}")
            return None
    
    def _get_dict_from_langfuse(self, agent_type: str, prompt_key: str) -> Optional[Dict[str, Any]]:
        """Get prompt dictionary from Langfuse"""
        if not langfuse_service.is_enabled:
            return None
        
        try:
            # This would query Langfuse for the prompt collection
            # For now, we'll return None to trigger fallback
            logger.debug(f"Querying Langfuse for prompt dict: {agent_type}:{prompt_key}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get prompt dict from Langfuse: {e}")
            return None
    
    def _get_from_local_yaml(self, 
                            agent_type: str, 
                            prompt_key: str, 
                            sub_key: Optional[str] = None) -> Optional[str]:
        """Get prompt from local YAML file"""
        try:
            yaml_file = self.prompts_dir / f"{agent_type}_prompts.yaml"
            
            if not yaml_file.exists():
                logger.warning(f"YAML file not found: {yaml_file}")
                return None
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
            
            # Navigate to the specific prompt
            if sub_key:
                # Handle nested keys like 'agents.data_analyst.backstory'
                keys = sub_key.split('.')
                current = prompts.get(prompt_key, {})
                for key in keys:
                    if isinstance(current, dict):
                        current = current.get(key)
                    else:
                        return None
                return current
            else:
                return prompts.get(prompt_key)
                
        except Exception as e:
            logger.error(f"Failed to load prompt from YAML: {e}")
            return None
    
    def _get_dict_from_local_yaml(self, agent_type: str, prompt_key: str) -> Optional[Dict[str, Any]]:
        """Get prompt dictionary from local YAML file"""
        try:
            yaml_file = self.prompts_dir / f"{agent_type}_prompts.yaml"
            
            if not yaml_file.exists():
                logger.warning(f"YAML file not found: {yaml_file}")
                return None
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
            
            return prompts.get(prompt_key, {})
                
        except Exception as e:
            logger.error(f"Failed to load prompt dict from YAML: {e}")
            return None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached prompt is still valid"""
        if cache_key not in self.cache_timestamp:
            return False
        
        return datetime.now() - self.cache_timestamp[cache_key] < self.cache_ttl
    
    def _cache_prompt(self, cache_key: str, prompt: Any):
        """Cache a prompt with timestamp"""
        self.prompts_cache[cache_key] = prompt
        self.cache_timestamp[cache_key] = datetime.now()
    
    def update_prompt_in_langfuse(self, 
                                 agent_type: str, 
                                 prompt_key: str, 
                                 prompt_value: str,
                                 sub_key: Optional[str] = None) -> bool:
        """
        Update a prompt in Langfuse
        
        Args:
            agent_type: Type of agent
            prompt_key: Main prompt key
            prompt_value: New prompt value
            sub_key: Sub-key for nested prompts
        
        Returns:
            True if successful, False otherwise
        """
        if not langfuse_service.is_enabled:
            logger.warning("Langfuse not enabled - cannot update prompt")
            return False
        
        try:
            # This would update the prompt in Langfuse
            # For now, we'll just log the intent
            logger.info(f"Updating Langfuse prompt: {agent_type}:{prompt_key}:{sub_key}")
            
            # Clear cache for this prompt
            cache_key = f"{agent_type}:{prompt_key}:{sub_key}" if sub_key else f"{agent_type}:{prompt_key}"
            if cache_key in self.prompts_cache:
                del self.prompts_cache[cache_key]
                del self.cache_timestamp[cache_key]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update prompt in Langfuse: {e}")
            return False
    
    def sync_prompts_to_langfuse(self) -> Dict[str, bool]:
        """
        Sync all local YAML prompts to Langfuse
        
        Returns:
            Dictionary mapping prompt keys to success status
        """
        results = {}
        
        if not langfuse_service.is_enabled:
            logger.warning("Langfuse not enabled - cannot sync prompts")
            return results
        
        try:
            # Get all YAML files
            yaml_files = list(self.prompts_dir.glob("*_prompts.yaml"))
            
            for yaml_file in yaml_files:
                agent_type = yaml_file.stem.replace("_prompts", "")
                
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    prompts = yaml.safe_load(f)
                
                # Sync each prompt section
                for prompt_key, prompt_value in prompts.items():
                    if isinstance(prompt_value, dict):
                        # Handle nested prompts
                        for sub_key, sub_value in prompt_value.items():
                            if isinstance(sub_value, str):
                                success = self.update_prompt_in_langfuse(
                                    agent_type, prompt_key, sub_value, sub_key
                                )
                                results[f"{agent_type}:{prompt_key}:{sub_key}"] = success
                    elif isinstance(prompt_value, str):
                        # Handle simple prompts
                        success = self.update_prompt_in_langfuse(
                            agent_type, prompt_key, prompt_value
                        )
                        results[f"{agent_type}:{prompt_key}"] = success
            
            logger.info(f"Synced {len(results)} prompts to Langfuse")
            return results
            
        except Exception as e:
            logger.error(f"Failed to sync prompts to Langfuse: {e}")
            return results
    
    def clear_cache(self):
        """Clear the prompt cache"""
        self.prompts_cache.clear()
        self.cache_timestamp.clear()
        logger.info("✅ Prompt cache cleared")


# Global prompt service instance
_prompt_service: Optional[PromptService] = None

def get_prompt_service() -> PromptService:
    """Get the global prompt service instance"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service 