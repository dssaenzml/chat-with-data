"""
LangGraph Orchestrator for Chat with Data
Coordinates between CrewAI agents and SQL analysis for comprehensive data insights
"""

import asyncio
import pandas as pd
from typing import Dict, Any, List, Optional, TypedDict, Annotated
import logging
from datetime import datetime

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

# CrewAI integration
from .crew_agent import CrewDataAgent
from .sql_agent import SQLAgent

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AnalysisState(TypedDict):
    """State for the analysis workflow"""
    query: str
    data_source: Dict[str, Any]
    analysis_type: str
    intent: str
    crew_result: Optional[Dict[str, Any]]
    sql_result: Optional[Dict[str, Any]]
    final_response: Optional[Dict[str, Any]]
    error: Optional[str]
    messages: List[Dict[str, Any]]

class LangGraphOrchestrator:
    """LangGraph orchestrator for intelligent data analysis workflows"""
    
    def __init__(self):
        self.llm = None
        self.crew_agent = CrewDataAgent()
        self.sql_agent = SQLAgent()
        self.graph = None
        self.memory = MemorySaver()
        self._initialize_llm()
        self._build_graph()
    
    def _initialize_llm(self):
        """Initialize LLM for orchestration"""
        try:
            if settings.openai_api_key:
                self.llm = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.1,
                    max_tokens=4000,
                    api_key=settings.openai_api_key
                )
                logger.info("✅ LangGraph LLM initialized")
            else:
                logger.warning("⚠️ No OpenAI API key provided - LangGraph will use mock responses")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LangGraph LLM: {e}")
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AnalysisState)
        
        # Add nodes
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("route_analysis", self._route_analysis)
        workflow.add_node("crew_analysis", self._crew_analysis)
        workflow.add_node("sql_analysis", self._sql_analysis)
        workflow.add_node("synthesize_results", self._synthesize_results)
        workflow.add_node("format_response", self._format_response)
        
        # Add edges
        workflow.set_entry_point("analyze_intent")
        workflow.add_edge("analyze_intent", "route_analysis")
        workflow.add_conditional_edges(
            "route_analysis",
            self._decide_analysis_path,
            {
                "crew_only": "crew_analysis",
                "sql_only": "sql_analysis", 
                "both": "crew_analysis",
                "error": END
            }
        )
        workflow.add_edge("crew_analysis", "synthesize_results")
        workflow.add_edge("sql_analysis", "synthesize_results")
        workflow.add_edge("synthesize_results", "format_response")
        workflow.add_edge("format_response", END)
        
        self.graph = workflow.compile(checkpointer=self.memory)
        logger.info("✅ LangGraph workflow built successfully")
    
    async def _analyze_intent(self, state: AnalysisState) -> AnalysisState:
        """Analyze the user's query intent"""
        try:
            query = state["query"]
            data_source = state["data_source"]
            
            # Create intent analysis prompt
            system_prompt = """You are an expert data analyst. Analyze the user's query and determine:
            1. What type of analysis they want (descriptive, comparative, predictive, etc.)
            2. What specific intent they have (summary, trend, correlation, etc.)
            3. Whether they need SQL database queries or data file analysis
            
            Return a structured analysis of their intent."""
            
            if self.llm:
                response = await self.llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Query: {query}\nData source: {data_source.get('type', 'unknown')}")
                ])
                
                # Extract intent from response
                intent_analysis = self._parse_intent_response(response.content)
                state["analysis_type"] = intent_analysis.get("analysis_type", "general")
                state["intent"] = intent_analysis.get("intent", "summary")
            else:
                # Mock response
                state["analysis_type"] = "general"
                state["intent"] = "summary"
            
            state["messages"].append({
                "role": "system",
                "content": f"Intent analyzed: {state['intent']} ({state['analysis_type']})",
                "timestamp": datetime.now().isoformat()
            })
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Intent analysis failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _route_analysis(self, state: AnalysisState) -> AnalysisState:
        """Determine which analysis path to take"""
        try:
            data_source = state["data_source"]
            query = state["query"].lower()
            
            # Determine if we need SQL, CrewAI, or both
            needs_sql = (
                data_source.get("type") == "database" or
                "sql" in query or
                "database" in query or
                "table" in query
            )
            
            needs_crew = (
                "analyze" in query or
                "compare" in query or
                "trend" in query or
                "insight" in query or
                "recommend" in query
            )
            
            if needs_sql and needs_crew:
                state["route"] = "both"
            elif needs_sql:
                state["route"] = "sql_only"
            else:
                state["route"] = "crew_only"
            
            logger.info(f"🎯 Analysis route determined: {state['route']}")
            return state
            
        except Exception as e:
            logger.error(f"❌ Routing failed: {e}")
            state["error"] = str(e)
            state["route"] = "error"
            return state
    
    def _decide_analysis_path(self, state: AnalysisState) -> str:
        """Conditional edge function to decide analysis path"""
        return state.get("route", "error")
    
    async def _crew_analysis(self, state: AnalysisState) -> AnalysisState:
        """Perform CrewAI analysis"""
        try:
            query = state["query"]
            data_source = state["data_source"]
            analysis_type = state["analysis_type"]
            
            # Get dataframe from data source
            df = await self._get_dataframe(data_source)
            
            if df is not None:
                crew_result = await self.crew_agent.analyze_with_crew(
                    query=query,
                    df=df,
                    analysis_type=analysis_type
                )
                state["crew_result"] = crew_result
                
                state["messages"].append({
                    "role": "assistant",
                    "content": "CrewAI analysis completed",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                state["crew_result"] = {"error": "Could not load data for analysis"}
            
            # If route is "both", continue to SQL analysis
            if state.get("route") == "both":
                return await self._sql_analysis(state)
            
            return state
            
        except Exception as e:
            logger.error(f"❌ CrewAI analysis failed: {e}")
            state["crew_result"] = {"error": str(e)}
            return state
    
    async def _sql_analysis(self, state: AnalysisState) -> AnalysisState:
        """Perform SQL analysis"""
        try:
            query = state["query"]
            data_source = state["data_source"]
            intent = state["intent"]
            
            sql_result = await self.sql_agent.process_query(
                query=query,
                data_source=data_source,
                intent=intent
            )
            state["sql_result"] = sql_result
            
            state["messages"].append({
                "role": "assistant", 
                "content": "SQL analysis completed",
                "timestamp": datetime.now().isoformat()
            })
            
            return state
            
        except Exception as e:
            logger.error(f"❌ SQL analysis failed: {e}")
            state["sql_result"] = {"error": str(e)}
            return state
    
    async def _synthesize_results(self, state: AnalysisState) -> AnalysisState:
        """Synthesize results from different analysis methods"""
        try:
            crew_result = state.get("crew_result")
            sql_result = state.get("sql_result")
            query = state["query"]
            
            # Combine insights from both sources
            synthesis_prompt = f"""
            You are synthesizing analysis results to answer this query: "{query}"
            
            CrewAI Analysis: {crew_result}
            SQL Analysis: {sql_result}
            
            Provide a comprehensive synthesis that:
            1. Combines insights from both analyses
            2. Resolves any conflicts or contradictions
            3. Highlights the most important findings
            4. Provides actionable recommendations
            """
            
            if self.llm and (crew_result or sql_result):
                response = await self.llm.ainvoke([
                    SystemMessage(content="You are an expert data analyst synthesizing multiple analysis results."),
                    HumanMessage(content=synthesis_prompt)
                ])
                
                synthesis = {
                    "synthesis": response.content,
                    "crew_result": crew_result,
                    "sql_result": sql_result,
                    "confidence": self._calculate_confidence(crew_result, sql_result)
                }
            else:
                # Fallback synthesis
                synthesis = {
                    "synthesis": "Analysis completed with available methods",
                    "crew_result": crew_result,
                    "sql_result": sql_result,
                    "confidence": 0.7
                }
            
            state["synthesis"] = synthesis
            return state
            
        except Exception as e:
            logger.error(f"❌ Synthesis failed: {e}")
            state["synthesis"] = {"error": str(e)}
            return state
    
    async def _format_response(self, state: AnalysisState) -> AnalysisState:
        """Format the final response"""
        try:
            synthesis = state.get("synthesis", {})
            query = state["query"]
            
            final_response = {
                "query": query,
                "answer": synthesis.get("synthesis", "Analysis completed"),
                "insights": self._extract_insights(synthesis),
                "visualizations": self._extract_visualizations(synthesis),
                "confidence": synthesis.get("confidence", 0.8),
                "analysis_type": state["analysis_type"],
                "timestamp": datetime.now().isoformat(),
                "sources": self._get_sources(state)
            }
            
            state["final_response"] = final_response
            
            state["messages"].append({
                "role": "assistant",
                "content": final_response["answer"],
                "timestamp": datetime.now().isoformat()
            })
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Response formatting failed: {e}")
            state["final_response"] = {"error": str(e)}
            return state
    
    async def analyze(self, 
                     query: str, 
                     data_source: Dict[str, Any], 
                     session_id: str = "default") -> Dict[str, Any]:
        """Main analysis method"""
        try:
            initial_state = AnalysisState(
                query=query,
                data_source=data_source,
                analysis_type="general",
                intent="summary", 
                crew_result=None,
                sql_result=None,
                final_response=None,
                error=None,
                messages=[]
            )
            
            # Run the workflow
            config = {"configurable": {"thread_id": session_id}}
            final_state = await self.graph.ainvoke(initial_state, config)
            
            return final_state.get("final_response", {"error": "Analysis failed"})
            
        except Exception as e:
            logger.error(f"❌ LangGraph analysis failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    # Helper methods
    
    def _parse_intent_response(self, response: str) -> Dict[str, str]:
        """Parse intent analysis response"""
        # Simple parsing - in production, use structured output
        response_lower = response.lower()
        
        if "comparative" in response_lower or "compare" in response_lower:
            return {"analysis_type": "comparative", "intent": "comparison"}
        elif "trend" in response_lower or "time" in response_lower:
            return {"analysis_type": "temporal", "intent": "trend"}
        elif "correlation" in response_lower or "relationship" in response_lower:
            return {"analysis_type": "correlation", "intent": "relationship"}
        else:
            return {"analysis_type": "general", "intent": "summary"}
    
    async def _get_dataframe(self, data_source: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Extract dataframe from data source"""
        try:
            if data_source.get("type") == "dataframe":
                return data_source.get("data")
            elif data_source.get("type") == "file":
                file_path = data_source.get("path")
                if file_path.endswith('.csv'):
                    return pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    return pd.read_excel(file_path)
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get dataframe: {e}")
            return None
    
    def _calculate_confidence(self, crew_result: Dict, sql_result: Dict) -> float:
        """Calculate confidence score based on analysis results"""
        confidence = 0.5
        
        if crew_result and not crew_result.get("error"):
            confidence += 0.3
        
        if sql_result and not sql_result.get("error"):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _extract_insights(self, synthesis: Dict) -> List[str]:
        """Extract key insights from synthesis"""
        insights = []
        
        crew_result = synthesis.get("crew_result", {})
        if crew_result and "insights" in crew_result:
            insights.extend(crew_result["insights"])
        
        sql_result = synthesis.get("sql_result", {})
        if sql_result and "insights" in sql_result:
            insights.extend(sql_result["insights"])
        
        return insights[:5]  # Top 5 insights
    
    def _extract_visualizations(self, synthesis: Dict) -> List[Dict]:
        """Extract visualization recommendations"""
        visualizations = []
        
        crew_result = synthesis.get("crew_result", {})
        if crew_result and "visualizations" in crew_result:
            visualizations.extend(crew_result["visualizations"])
        
        return visualizations
    
    def _get_sources(self, state: AnalysisState) -> List[str]:
        """Get analysis sources used"""
        sources = []
        
        if state.get("crew_result"):
            sources.append("CrewAI Multi-Agent Analysis")
        
        if state.get("sql_result"):
            sources.append("SQL Database Analysis")
        
        return sources 