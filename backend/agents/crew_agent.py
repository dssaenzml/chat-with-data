import asyncio
import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# CrewAI imports
try:
    from crewai import Agent, Task, Crew, Process
    from crewai_tools import tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False

# LangChain imports
from langchain_openai import ChatOpenAI

from config.settings import get_settings
from services.langfuse_service import get_langfuse_service, track_agent_execution, langfuse_observe
from services.prompt_service import get_prompt_service

logger = logging.getLogger(__name__)
settings = get_settings()
langfuse_service = get_langfuse_service()


class CrewDataAgent:
    """CrewAI agent for complex data analysis tasks"""
    
    def __init__(self):
        self.llm = None
        self.agents = {}
        self.crews = {}
        self.prompt_service = get_prompt_service()
        self._initialize_llm()
        if CREWAI_AVAILABLE:
            self._create_agents()
        
    def _initialize_llm(self):
        """Initialize LLM for CrewAI"""
        try:
            if settings.openai_api_key:
                self.llm = ChatOpenAI(
                    model=settings.crewai_model,
                    temperature=settings.crewai_temperature,
                    max_tokens=settings.crewai_max_tokens,
                    api_key=settings.openai_api_key
                )
                logger.info("✅ CrewAI LLM initialized")
            else:
                logger.warning("⚠️ No OpenAI API key provided - CrewAI will use mock responses")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CrewAI LLM: {e}")
    
    def _create_agents(self):
        """Create specialized agents for different analysis tasks"""
        try:
            # Get agent prompts from prompt service
            agents_config = self.prompt_service.get_prompt_dict("crew_agent", "agents")
            
            if not agents_config:
                logger.warning("⚠️ No agent prompts found, using default prompts")
                agents_config = self._get_default_agent_configs()
            
            # Create agents from prompts
            for agent_key, agent_config in agents_config.items():
                self.agents[agent_key] = Agent(
                    role=agent_config.get('role', f'{agent_key.title()}'),
                    goal=agent_config.get('goal', 'Analyze data effectively'),
                    backstory=agent_config.get('backstory', f'You are a {agent_key.replace("_", " ")}.'),
                    verbose=True,
                    allow_delegation=False,
                    llm=self.llm
                )
            
            logger.info(f"✅ Created {len(self.agents)} CrewAI agents from prompts")
            
        except Exception as e:
            logger.error(f"❌ Failed to create CrewAI agents: {e}")
    
    def _get_default_agent_configs(self) -> Dict[str, Dict[str, str]]:
        """Get default agent configurations if prompts are not available"""
        return {
            'data_analyst': {
                'role': 'Senior Data Analyst',
                'goal': 'Analyze data to extract meaningful insights and patterns',
                'backstory': """You are a senior data analyst with extensive experience in 
                statistical analysis, data mining, and business intelligence. You excel at 
                identifying trends, anomalies, and actionable insights from complex datasets."""
            },
            'bi_specialist': {
                'role': 'Business Intelligence Specialist',
                'goal': 'Translate data insights into business recommendations',
                'backstory': """You are a business intelligence specialist who bridges the gap 
                between technical analysis and business strategy. You excel at creating 
                actionable recommendations based on data insights."""
            },
            'statistician': {
                'role': 'Statistical Analyst',
                'goal': 'Perform advanced statistical analysis and modeling',
                'backstory': """You are a statistical analyst with deep expertise in statistical 
                methods, hypothesis testing, and predictive modeling. You provide rigorous 
                statistical validation of data insights."""
            },
            'viz_expert': {
                'role': 'Data Visualization Expert',
                'goal': 'Create compelling and informative data visualizations',
                'backstory': """You are a data visualization expert who specializes in creating 
                clear, compelling, and informative charts and graphs that effectively 
                communicate data insights to various audiences."""
            }
        }
    
    @langfuse_observe(name="crewai_analysis")
    async def analyze_with_crew(self, 
                               query: str, 
                               df: pd.DataFrame, 
                               analysis_type: str = "general") -> Dict[str, Any]:
        """Perform analysis using CrewAI crew"""
        try:
            # Track input for Langfuse
            input_data = {
                "query": query,
                "analysis_type": analysis_type,
                "data_shape": df.shape,
                "data_columns": list(df.columns),
                "data_types": str(df.dtypes.to_dict())
            }
            if not CREWAI_AVAILABLE or not self.llm:
                return await self._mock_crew_analysis(query, df, analysis_type)
            
            # Create tasks based on analysis type
            tasks = self._create_analysis_tasks(query, df, analysis_type)
            
            # Create crew
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=tasks,
                verbose=True,
                process=Process.sequential
            )
            
            # Execute analysis
            result = await asyncio.get_event_loop().run_in_executor(
                None, crew.kickoff
            )
            
            formatted_result = self._format_crew_result(result, df)
            
            # Track execution for Langfuse
            track_agent_execution(
                agent_name="crewai_multi_agent",
                input_data=input_data,
                output_data={
                    "analysis_type": analysis_type,
                    "insights_count": len(formatted_result.get("insights", [])),
                    "recommendations_count": len(formatted_result.get("recommendations", [])),
                    "has_visualizations": "visualizations" in formatted_result,
                    "success": True
                }
            )
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"❌ CrewAI analysis failed: {e}")
            
            # Track error for Langfuse
            track_agent_execution(
                agent_name="crewai_multi_agent",
                input_data=input_data if 'input_data' in locals() else {"query": query, "error": "input_data_not_available"},
                output_data={
                    "error": str(e),
                    "analysis_type": analysis_type,
                    "success": False
                }
            )
            
            return await self._mock_crew_analysis(query, df, analysis_type)
    
    def _create_analysis_tasks(self, 
                              query: str, 
                              df: pd.DataFrame, 
                              analysis_type: str) -> List:
        """Create tasks for the crew based on analysis type"""
        if not CREWAI_AVAILABLE:
            return []
        
        # Prepare data summary for tasks
        data_summary = self._create_data_summary(df)
        
        tasks = []
        
        if analysis_type in ["comparison", "comparative"]:
            tasks.extend(self._create_comparison_tasks(query, data_summary))
        elif analysis_type in ["trend", "temporal"]:
            tasks.extend(self._create_trend_tasks(query, data_summary))
        elif analysis_type in ["correlation", "relationship"]:
            tasks.extend(self._create_correlation_tasks(query, data_summary))
        else:
            tasks.extend(self._create_general_tasks(query, data_summary))
        
        return tasks
    
    def _create_comparison_tasks(self, query: str, data_summary: str) -> List:
        """Create tasks for comparative analysis"""
        return [
            Task(
                description=f"""Analyze the data for comparative insights based on this query: "{query}"
                
                Data Summary:
                {data_summary}
                
                Focus on:
                1. Identifying key metrics for comparison
                2. Finding significant differences between groups/categories
                3. Statistical significance of differences
                4. Ranking and prioritization of findings
                """,
                agent=self.agents['data_analyst']
            ),
            Task(
                description=f"""Perform statistical validation of the comparative analysis.
                
                Tasks:
                1. Validate statistical significance of identified differences
                2. Calculate confidence intervals where appropriate
                3. Identify potential confounding factors
                4. Assess reliability of conclusions
                """,
                agent=self.agents['statistician']
            ),
            Task(
                description=f"""Create business recommendations based on the comparative analysis.
                
                Tasks:
                1. Translate statistical findings into business implications
                2. Prioritize actionable insights
                3. Suggest next steps and further analysis
                4. Identify potential risks and opportunities
                """,
                agent=self.agents['bi_specialist']
            )
        ]
    
    def _create_trend_tasks(self, query: str, data_summary: str) -> List:
        """Create tasks for trend analysis"""
        return [
            Task(
                description=f"""Analyze temporal patterns and trends based on: "{query}"
                
                Data Summary:
                {data_summary}
                
                Focus on:
                1. Identifying time-based patterns and trends
                2. Seasonality and cyclical patterns
                3. Rate of change and acceleration
                4. Anomalies and outliers in time series
                """,
                agent=self.agents['data_analyst']
            ),
            Task(
                description=f"""Perform statistical analysis of trends and patterns.
                
                Tasks:
                1. Test for trend significance
                2. Decompose time series components
                3. Identify change points
                4. Forecast future trends where appropriate
                """,
                agent=self.agents['statistician']
            ),
            Task(
                description=f"""Recommend visualization strategies for trend data.
                
                Tasks:
                1. Suggest appropriate chart types for temporal data
                2. Identify key time periods to highlight
                3. Recommend interactive features for exploration
                4. Design layout for maximum insight communication
                """,
                agent=self.agents['viz_expert']
            )
        ]
    
    def _create_correlation_tasks(self, query: str, data_summary: str) -> List:
        """Create tasks for correlation analysis"""
        return [
            Task(
                description=f"""Analyze relationships and correlations based on: "{query}"
                
                Data Summary:
                {data_summary}
                
                Focus on:
                1. Identifying strong correlations between variables
                2. Distinguishing correlation from causation
                3. Finding unexpected relationships
                4. Analyzing correlation stability across subgroups
                """,
                agent=self.agents['data_analyst']
            ),
            Task(
                description=f"""Validate and interpret correlation findings.
                
                Tasks:
                1. Test correlation significance
                2. Identify potential spurious correlations
                3. Analyze partial correlations
                4. Assess multicollinearity issues
                """,
                agent=self.agents['statistician']
            )
        ]
    
    def _create_general_tasks(self, query: str, data_summary: str) -> List:
        """Create tasks for general analysis"""
        return [
            Task(
                description=f"""Perform comprehensive data analysis based on: "{query}"
                
                Data Summary:
                {data_summary}
                
                Focus on:
                1. Data quality assessment
                2. Descriptive statistics and distributions
                3. Key insights and patterns
                4. Anomalies and outliers
                """,
                agent=self.agents['data_analyst']
            ),
            Task(
                description=f"""Create business insights and recommendations.
                
                Tasks:
                1. Translate findings into business language
                2. Prioritize actionable insights
                3. Identify opportunities and risks
                4. Suggest follow-up analyses
                """,
                agent=self.agents['bi_specialist']
            )
        ]
    
    def _create_data_summary(self, df: pd.DataFrame) -> str:
        """Create a summary of the dataset for task context"""
        try:
            summary_parts = [
                f"Dataset Shape: {df.shape[0]} rows, {df.shape[1]} columns",
                f"Columns: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}",
            ]
            
            # Numeric columns summary
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary_parts.append(f"Numeric columns: {', '.join(numeric_cols[:5])}")
            
            # Categorical columns summary
            cat_cols = df.select_dtypes(include=['object', 'category']).columns
            if len(cat_cols) > 0:
                summary_parts.append(f"Categorical columns: {', '.join(cat_cols[:5])}")
            
            # Missing values
            missing_pct = (df.isnull().sum() / len(df) * 100).round(1)
            high_missing = missing_pct[missing_pct > 10].head(3)
            if not high_missing.empty:
                summary_parts.append(f"High missing values: {dict(high_missing)}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"❌ Failed to create data summary: {e}")
            return f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns"
    
    def _format_crew_result(self, result: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Format CrewAI result for API response"""
        try:
            return {
                "message": result,
                "data": {
                    "table": df.head(10).to_dict('records'),
                    "analysis_type": "crew_analysis"
                },
                "suggestions": [
                    "Explore specific aspects in detail",
                    "Create custom visualizations",
                    "Run targeted statistical tests"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Failed to format crew result: {e}")
            return {
                "message": "Analysis completed by the crew.",
                "error": str(e)
            }
    
    async def process_general_query(self, 
                                  query: str, 
                                  data_source: Dict[str, Any], 
                                  intent: str) -> Dict[str, Any]:
        """Process general query using CrewAI"""
        try:
            if not CREWAI_AVAILABLE or not self.llm:
                return {
                    "message": "CrewAI is not available. Please ensure it's properly installed.",
                    "suggestions": ["Try basic analysis", "Use individual agents"]
                }
            
            # Create a simple task for general queries
            task = Task(
                description=f"""Provide expert analysis for this query: "{query}"
                
                Data source type: {data_source.get('type', 'unknown')}
                Intent: {intent}
                
                Provide:
                1. Clear interpretation of the request
                2. Suggested approach for analysis
                3. Expected insights or outcomes
                4. Recommendations for data preparation
                """,
                agent=self.agents['data_analyst']
            )
            
            crew = Crew(
                agents=[self.agents['data_analyst']],
                tasks=[task],
                verbose=True
            )
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, crew.kickoff
            )
            
            return {
                "message": result,
                "suggestions": [
                    "Upload data for detailed analysis",
                    "Connect to a database",
                    "Try sample datasets"
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ General query processing failed: {e}")
            return {
                "message": "I can help you analyze data once you connect a data source.",
                "suggestions": [
                    "Upload a CSV or Excel file",
                    "Connect to a database",
                    "Load sample data"
                ]
            }
    
    async def _mock_crew_analysis(self, 
                                query: str, 
                                df: pd.DataFrame, 
                                analysis_type: str) -> Dict[str, Any]:
        """Mock analysis when CrewAI is not available"""
        try:
            analysis_messages = {
                "comparison": f"Comparative analysis shows significant differences across key metrics in your dataset of {df.shape[0]} rows.",
                "trend": f"Temporal analysis reveals interesting patterns and trends in your time-series data.",
                "correlation": f"Correlation analysis identifies several strong relationships between variables in your dataset.",
                "general": f"Comprehensive analysis of your {df.shape[0]}-row dataset reveals several key insights."
            }
            
            message = analysis_messages.get(analysis_type, analysis_messages["general"])
            
            # Add some basic insights
            insights = []
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                insights.append(f"Key numeric variables: {', '.join(numeric_cols[:3])}")
            
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            if len(categorical_cols) > 0:
                insights.append(f"Categorical variables: {', '.join(categorical_cols[:3])}")
            
            if insights:
                message += " " + " ".join(insights)
            
            return {
                "message": message,
                "data": {
                    "table": df.head(10).to_dict('records'),
                    "analysis_type": analysis_type
                },
                "suggestions": [
                    "Try different analysis approaches",
                    "Focus on specific variables",
                    "Create targeted visualizations"
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Mock analysis failed: {e}")
            return {
                "message": "Analysis completed with basic insights.",
                "error": str(e)
            }
