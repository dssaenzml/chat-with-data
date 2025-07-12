import asyncio
import pandas as pd
import sqlparse
from typing import Dict, Any, List, Optional
import logging
import re
from datetime import datetime

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from config.settings import get_settings
from services.prompt_service import get_prompt_service

logger = logging.getLogger(__name__)
settings = get_settings()


class SQLAgent:
    """SQL generation agent using LangGraph"""
    
    def __init__(self):
        self.llm = None
        self.prompt_service = get_prompt_service()
        self._initialize_model()
        self._setup_prompts()
    
    def _initialize_model(self):
        """Initialize LLM model"""
        try:
            if settings.openai_api_key:
                self.llm = ChatOpenAI(
                    model="gpt-4",
                    temperature=0.1,  # Lower temperature for more precise SQL
                    api_key=settings.openai_api_key
                )
                logger.info("✅ SQL agent model initialized")
            else:
                logger.warning("⚠️ No OpenAI API key provided - using mock responses")
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQL model: {e}")
    
    def _setup_prompts(self):
        """Setup prompt templates for SQL generation"""
        # Get prompts from prompt service
        sql_system_prompt = self.prompt_service.get_prompt("sql_agent", "sql_generation", "system_prompt")
        sql_human_template = self.prompt_service.get_prompt("sql_agent", "sql_generation", "human_template")
        
        pandas_system_prompt = self.prompt_service.get_prompt("sql_agent", "pandas_operations", "system_prompt")
        pandas_human_template = self.prompt_service.get_prompt("sql_agent", "pandas_operations", "human_template")
        
        # Use default prompts if not found
        if not sql_system_prompt:
            sql_system_prompt = """You are an expert SQL query generator. Given a natural language question and database schema information, generate a precise SQL query.

Rules:
1. Generate only valid SQL syntax
2. Use appropriate JOINs when needed
3. Include proper WHERE clauses for filtering
4. Use meaningful aliases for readability
5. Add comments for complex queries
6. Return only the SQL query, no explanations

Database Schema Information:
{schema_info}

Previous conversation context:
{chat_history}"""
        
        if not sql_human_template:
            sql_human_template = "Generate SQL query for: {question}"
        
        if not pandas_system_prompt:
            pandas_system_prompt = """You are an expert at converting natural language questions into pandas operations. Given a DataFrame structure and a question, generate pandas code to answer it.

Rules:
1. Use only pandas operations
2. Return executable Python code
3. Assume the DataFrame is named 'df'
4. Handle missing values appropriately
5. Return only the code, no explanations

DataFrame Information:
Columns: {columns}
Data types: {dtypes}
Shape: {shape}
Sample data:
{sample_data}"""
        
        if not pandas_human_template:
            pandas_human_template = "Generate pandas code for: {question}"
        
        self.sql_prompt = ChatPromptTemplate.from_messages([
            ("system", sql_system_prompt),
            ("human", sql_human_template)
        ])
        
        self.pandas_prompt = ChatPromptTemplate.from_messages([
            ("system", pandas_system_prompt),
            ("human", pandas_human_template)
        ])
    
    async def generate_sql_query(self, 
                                message: str,
                                schema_info: List[Dict[str, Any]] = None,
                                chat_history: List[Dict[str, Any]] = None) -> Optional[str]:
        """Generate SQL query from natural language"""
        try:
            if not self.llm:
                return self._generate_mock_sql(message)
            
            # Format schema information
            schema_text = self._format_schema_info(schema_info or [])
            
            # Format chat history
            history_text = self._format_chat_history(chat_history or [])
            
            # Create chain
            chain = self.sql_prompt | self.llm | StrOutputParser()
            
            # Generate query
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: chain.invoke({
                    "question": message,
                    "schema_info": schema_text,
                    "chat_history": history_text
                })
            )
            
            # Clean and validate SQL
            sql_query = self._clean_sql_query(result)
            
            if self._validate_sql_query(sql_query):
                return sql_query
            else:
                logger.warning(f"Generated invalid SQL: {sql_query}")
                return None
                
        except Exception as e:
            logger.error(f"❌ SQL generation failed: {e}")
            return None
    
    async def generate_pandas_query(self, 
                                  message: str, 
                                  df: pd.DataFrame) -> Dict[str, Any]:
        """Generate pandas operations for DataFrame analysis"""
        try:
            if not self.llm:
                return self._generate_mock_pandas_result(message, df)
            
            # Prepare DataFrame information
            df_info = {
                "columns": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "shape": df.shape,
                "sample_data": df.head(3).to_string()
            }
            
            # Create chain
            chain = self.pandas_prompt | self.llm | StrOutputParser()
            
            # Generate pandas code
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: chain.invoke({
                    "question": message,
                    **df_info
                })
            )
            
            # Clean pandas code
            pandas_code = self._clean_pandas_code(result)
            
            # Execute pandas code safely
            execution_result = await self._execute_pandas_code(pandas_code, df)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Pandas query generation failed: {e}")
            return {"message": f"Error generating pandas query: {str(e)}"}
    
    def _format_schema_info(self, schema_info: List[Dict[str, Any]]) -> str:
        """Format schema information for prompt"""
        if not schema_info:
            return "No schema information available."
        
        schema_parts = []
        for item in schema_info:
            if "metadata" in item and "schema_info" in item["metadata"]:
                schema_data = item["metadata"]["schema_info"]
                if "tables" in schema_data:
                    for table in schema_data["tables"]:
                        table_name = table.get("name", "unknown")
                        schema_parts.append(f"\nTable: {table_name}")
                        
                        if "columns" in table:
                            for column in table["columns"]:
                                col_name = column.get("name", "")
                                col_type = column.get("type", "")
                                schema_parts.append(f"  - {col_name} ({col_type})")
        
        return "\n".join(schema_parts) if schema_parts else "No detailed schema available."
    
    def _format_chat_history(self, chat_history: List[Dict[str, Any]]) -> str:
        """Format chat history for context"""
        if not chat_history:
            return "No previous conversation."
        
        history_parts = []
        for msg in chat_history[-5:]:  # Last 5 messages
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role and content:
                history_parts.append(f"{role}: {content[:100]}")
        
        return "\n".join(history_parts)
    
    def _clean_sql_query(self, query: str) -> str:
        """Clean and format SQL query"""
        # Remove markdown formatting
        query = re.sub(r'```sql\n?', '', query)
        query = re.sub(r'```\n?', '', query)
        
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Ensure query ends with semicolon
        if not query.endswith(';'):
            query += ';'
        
        return query
    
    def _clean_pandas_code(self, code: str) -> str:
        """Clean pandas code"""
        # Remove markdown formatting
        code = re.sub(r'```python\n?', '', code)
        code = re.sub(r'```\n?', '', code)
        
        # Remove comments and docstrings
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _validate_sql_query(self, query: str) -> bool:
        """Validate SQL query syntax"""
        try:
            # Basic validation using sqlparse
            parsed = sqlparse.parse(query)
            if not parsed:
                return False
            
            # Check for SQL injection patterns (basic)
            dangerous_patterns = [
                r';\s*drop\s+table',
                r';\s*delete\s+from',
                r';\s*insert\s+into',
                r';\s*update\s+.*\s+set',
                r'union\s+select.*from'
            ]
            
            query_lower = query.lower()
            for pattern in dangerous_patterns:
                if re.search(pattern, query_lower):
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _execute_pandas_code(self, code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Safely execute pandas code"""
        try:
            # Create a safe environment for execution
            safe_globals = {
                'df': df.copy(),
                'pd': pd,
                'np': __import__('numpy'),
                'datetime': datetime
            }
            
            # Restricted builtins
            safe_builtins = {
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round
            }
            
            safe_globals['__builtins__'] = safe_builtins
            
            # Execute code
            exec_result = None
            local_vars = {}
            
            # Execute in separate thread to prevent blocking
            def execute():
                exec(code, safe_globals, local_vars)
                # Try to get the result from the last expression
                if 'result' in local_vars:
                    return local_vars['result']
                else:
                    # Look for DataFrame operations
                    for var_name, var_value in local_vars.items():
                        if isinstance(var_value, (pd.DataFrame, pd.Series)):
                            return var_value
                    return "Code executed successfully"
            
            exec_result = await asyncio.get_event_loop().run_in_executor(None, execute)
            
            # Format result
            if isinstance(exec_result, pd.DataFrame):
                return {
                    "message": f"Query executed successfully. Found {len(exec_result)} results.",
                    "data": {
                        "table": exec_result.head(20).to_dict('records'),
                        "code": code
                    },
                    "suggestions": [
                        "Show more results",
                        "Apply additional filters",
                        "Visualize this data"
                    ]
                }
            elif isinstance(exec_result, pd.Series):
                return {
                    "message": "Query executed successfully.",
                    "data": {
                        "table": exec_result.head(20).to_frame().to_dict('records'),
                        "code": code
                    },
                    "suggestions": ["Convert to visualization", "Show detailed analysis"]
                }
            else:
                return {
                    "message": f"Query result: {str(exec_result)}",
                    "data": {"code": code, "result": str(exec_result)},
                    "suggestions": ["Try a different query", "Show data summary"]
                }
                
        except Exception as e:
            logger.error(f"❌ Pandas code execution failed: {e}")
            return {
                "message": f"Error executing query: {str(e)}",
                "data": {"code": code, "error": str(e)},
                "suggestions": ["Check query syntax", "Try a simpler query"]
            }
    
    def _generate_mock_sql(self, message: str) -> str:
        """Generate mock SQL query when LLM is not available"""
        message_lower = message.lower()
        
        if "select" in message_lower:
            return "SELECT * FROM table_name LIMIT 10;"
        elif "count" in message_lower:
            return "SELECT COUNT(*) FROM table_name;"
        elif "average" in message_lower or "avg" in message_lower:
            return "SELECT AVG(column_name) FROM table_name;"
        elif "sum" in message_lower:
            return "SELECT SUM(column_name) FROM table_name;"
        elif "group" in message_lower:
            return "SELECT column_name, COUNT(*) FROM table_name GROUP BY column_name;"
        else:
            return "SELECT * FROM table_name WHERE condition = 'value';"
    
    def _generate_mock_pandas_result(self, message: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate mock pandas result when LLM is not available"""
        message_lower = message.lower()
        
        try:
            if "count" in message_lower:
                result = df.shape[0]
                return {
                    "message": f"Total count: {result}",
                    "data": {"result": result},
                    "suggestions": ["Show data summary", "Analyze columns"]
                }
            elif "average" in message_lower or "mean" in message_lower:
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    result = df[numeric_cols[0]].mean()
                    return {
                        "message": f"Average of {numeric_cols[0]}: {result:.2f}",
                        "data": {"result": result},
                        "suggestions": ["Show other statistics", "Visualize distribution"]
                    }
            elif "filter" in message_lower:
                result_df = df.head(10)
                return {
                    "message": f"Showing filtered results ({len(result_df)} rows)",
                    "data": {"table": result_df.to_dict('records')},
                    "suggestions": ["Apply different filters", "Show all data"]
                }
            else:
                result_df = df.head(10)
                return {
                    "message": f"Showing sample data ({len(result_df)} rows)",
                    "data": {"table": result_df.to_dict('records')},
                    "suggestions": ["Show more data", "Apply filters", "Analyze columns"]
                }
                
        except Exception as e:
            return {
                "message": f"Error processing request: {str(e)}",
                "suggestions": ["Try a different query"]
            }
