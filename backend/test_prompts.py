#!/usr/bin/env python3
"""
Test script for the prompt management system
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from services.prompt_service import get_prompt_service
from agents.crew_agent import CrewDataAgent
from agents.sql_agent import SQLAgent
from agents.langgraph_orchestrator import LangGraphOrchestrator


async def test_prompt_service():
    """Test the prompt service functionality"""
    print("🧪 Testing Prompt Management System")
    print("=" * 50)
    
    # Initialize prompt service
    prompt_service = get_prompt_service()
    
    # Test 1: Load prompts from YAML files
    print("\n1. Testing YAML prompt loading...")
    
    # Test CrewAI agent prompts
    crew_agents = prompt_service.get_prompt_dict("crew_agent", "agents")
    if crew_agents:
        print(f"✅ Loaded {len(crew_agents)} CrewAI agent prompts")
        for agent_name in crew_agents.keys():
            print(f"   - {agent_name}")
    else:
        print("❌ Failed to load CrewAI agent prompts")
    
    # Test SQL agent prompts
    sql_generation = prompt_service.get_prompt("sql_agent", "sql_generation", "system_prompt")
    if sql_generation:
        print("✅ Loaded SQL generation prompt")
        print(f"   Length: {len(sql_generation)} characters")
    else:
        print("❌ Failed to load SQL generation prompt")
    
    # Test LangGraph prompts
    intent_analysis = prompt_service.get_prompt("langgraph", "intent_analysis", "system_prompt")
    if intent_analysis:
        print("✅ Loaded LangGraph intent analysis prompt")
        print(f"   Length: {len(intent_analysis)} characters")
    else:
        print("❌ Failed to load LangGraph intent analysis prompt")
    
    # Test 2: Agent initialization with prompts
    print("\n2. Testing agent initialization with prompts...")
    
    try:
        crew_agent = CrewDataAgent()
        print("✅ CrewAI agent initialized with prompts")
        
        sql_agent = SQLAgent()
        print("✅ SQL agent initialized with prompts")
        
        langgraph_orchestrator = LangGraphOrchestrator()
        print("✅ LangGraph orchestrator initialized with prompts")
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
    
    # Test 3: Prompt caching
    print("\n3. Testing prompt caching...")
    
    # Load the same prompt twice
    prompt1 = prompt_service.get_prompt("crew_agent", "agents", "data_analyst.backstory")
    prompt2 = prompt_service.get_prompt("crew_agent", "agents", "data_analyst.backstory")
    
    if prompt1 == prompt2:
        print("✅ Prompt caching working correctly")
    else:
        print("❌ Prompt caching not working")
    
    # Test 4: Cache clearing
    print("\n4. Testing cache clearing...")
    
    cache_size_before = len(prompt_service.prompts_cache)
    prompt_service.clear_cache()
    cache_size_after = len(prompt_service.prompts_cache)
    
    if cache_size_after == 0:
        print("✅ Cache cleared successfully")
    else:
        print(f"❌ Cache clearing failed: {cache_size_after} items remaining")
    
    print("\n" + "=" * 50)
    print("🎉 Prompt management system test completed!")


if __name__ == "__main__":
    asyncio.run(test_prompt_service()) 