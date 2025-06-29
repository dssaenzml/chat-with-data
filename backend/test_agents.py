#!/usr/bin/env python3
"""
Test script for CrewAI and LangGraph agents
Verifies that the new architecture is working properly
"""

import asyncio
import pandas as pd
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent))

from agents.crew_agent import CrewDataAgent
from agents.langgraph_orchestrator import LangGraphOrchestrator
from agents.sql_agent import SQLAgent

async def test_crew_agent():
    """Test CrewAI agent functionality"""
    print("🤖 Testing CrewAI Agent...")
    
    try:
        # Create sample data
        data = {
            'product': ['A', 'B', 'C', 'A', 'B'],
            'sales': [100, 150, 200, 120, 180],
            'region': ['North', 'South', 'North', 'South', 'North']
        }
        df = pd.DataFrame(data)
        
        # Initialize agent
        crew_agent = CrewDataAgent()
        
        # Test analysis
        result = await crew_agent.analyze_with_crew(
            query="What are the top products by sales?",
            df=df,
            analysis_type="general"
        )
        
        print("✅ CrewAI Agent test passed")
        print(f"   Result keys: {list(result.keys()) if result else 'None'}")
        return True
        
    except Exception as e:
        print(f"❌ CrewAI Agent test failed: {e}")
        return False

async def test_langgraph_orchestrator():
    """Test LangGraph orchestrator functionality"""
    print("🔗 Testing LangGraph Orchestrator...")
    
    try:
        # Create sample data source
        data_source = {
            "type": "dataframe",
            "data": pd.DataFrame({
                'product': ['A', 'B', 'C'],
                'sales': [100, 150, 200],
                'region': ['North', 'South', 'North']
            })
        }
        
        # Initialize orchestrator
        orchestrator = LangGraphOrchestrator()
        
        # Test analysis
        result = await orchestrator.analyze(
            query="Analyze the sales data and provide insights",
            data_source=data_source,
            session_id="test_session"
        )
        
        print("✅ LangGraph Orchestrator test passed")
        print(f"   Result keys: {list(result.keys()) if result else 'None'}")
        return True
        
    except Exception as e:
        print(f"❌ LangGraph Orchestrator test failed: {e}")
        return False

async def test_sql_agent():
    """Test SQL agent functionality"""
    print("🗄️  Testing SQL Agent...")
    
    try:
        # Initialize agent
        sql_agent = SQLAgent()
        
        # Test with mock data source
        data_source = {
            "type": "database",
            "connection_string": "sqlite:///:memory:"
        }
        
        result = await sql_agent.generate_sql_query(
            message="Show me the database schema",
            schema_info=[],
            chat_history=[]
        )
        
        print("✅ SQL Agent test passed")
        print(f"   Result: {result[:50] if result else 'None'}...")
        return True
        
    except Exception as e:
        print(f"❌ SQL Agent test failed: {e}")
        return False

async def test_langfuse_service():
    """Test Langfuse service functionality"""
    print("📊 Testing Langfuse Service...")
    
    try:
        from services.langfuse_service import get_langfuse_service, track_agent_execution
        
        langfuse_service = get_langfuse_service()
        print(f"✅ Langfuse Service created")
        print(f"   - Enabled: {langfuse_service.settings.langfuse_enabled}")
        print(f"   - Host: {langfuse_service.settings.langfuse_host}")
        print(f"   - Initialized: {langfuse_service.is_enabled}")
        
        # Test tracking (will only work if properly configured)
        track_agent_execution(
            agent_name="test_agent",
            input_data={"test": "data", "timestamp": "2024-01-01"},
            output_data={"result": "success", "test_completed": True}
        )
        print("✅ Test tracking completed (check Langfuse dashboard if enabled)")
        return True
        
    except Exception as e:
        print(f"⚠️ Langfuse test failed: {e}")
        print("   This is expected if Langfuse is not configured")
        return False

async def main():
    """Run all agent tests"""
    print("🧪 Testing Chat with Data Agents (CrewAI + LangGraph)")
    print("=" * 60)
    
    tests = [
        ("CrewAI Agent", test_crew_agent),
        ("LangGraph Orchestrator", test_langgraph_orchestrator),
        ("SQL Agent", test_sql_agent),
        ("Langfuse Service", test_langfuse_service)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n📋 Running {name} test...")
        success = await test_func()
        results.append((name, success))
        print()
    
    print("=" * 60)
    print("🏁 Test Results Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {name}: {status}")
        if not success:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All tests passed! Your CrewAI + LangGraph setup is working!")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("💡 This might be due to missing API keys or dependencies.")
    
    print("\n📚 Next steps:")
    print("   1. Add your OpenAI API key to .env file")
    print("   2. [Optional] Configure Langfuse for LLM observability:")
    print("      - Set LANGFUSE_ENABLED=true in .env")
    print("      - Add your Langfuse keys (see backend/docs/LANGFUSE_INTEGRATION.md)")
    print("   3. Run: docker-compose up -d")
    print("   4. Access the app at http://localhost:3000")

if __name__ == "__main__":
    asyncio.run(main()) 