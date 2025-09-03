"""
BigQuery AI Query Handler
Processes natural language queries and converts them to SQL using AI
"""

import logging
import json
from typing import Dict, Any, List, Optional
try:
    from google.cloud import bigquery
    BIGQUERY_AVAILABLE = True
except ImportError:
    bigquery = None
    BIGQUERY_AVAILABLE = False
import os
from datetime import datetime
import re

from openai import AsyncOpenAI
from .utils import get_env_var
from .schema_manager import SchemaManager
from .supabase_client import get_supabase_manager

logger = logging.getLogger(__name__)


class BigQueryAI:
    """AI-powered BigQuery query handler"""
    
    def __init__(self):
        """Initialize BigQuery AI handler"""
        # Initialize OpenAI client
        self.openai = AsyncOpenAI(
            api_key=get_env_var("OPENAI_API_KEY")
        )
        
        # Initialize BigQuery client
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.dataset_id = os.getenv("BIGQUERY_DATASET")
        
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            # Use service account file if available
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            self.bigquery_client = bigquery.Client(
                credentials=credentials,
                project=self.project_id
            )
            self.enabled = True
            logger.info("BigQuery AI initialized with service account file")
        elif self.project_id:
            # Use default application credentials (for Cloud Run)
            self.bigquery_client = bigquery.Client(project=self.project_id)
            self.enabled = True
            logger.info("BigQuery AI initialized with default credentials")
        else:
            self.bigquery_client = None
            self.enabled = False
            logger.warning("BigQuery AI disabled - no project ID specified")
        
        # Initialize schema manager
        self.schema_manager = SchemaManager()
        
        # Initialize Supabase for query logging
        self.supabase = get_supabase_manager()
        
        # Safety settings
        self.max_rows = int(os.getenv("BIGQUERY_MAX_ROWS", "10000"))
        self.timeout_seconds = int(os.getenv("BIGQUERY_TIMEOUT_SECONDS", "30"))
    
    async def process_query(self, user_query: str, language: str = "auto") -> Dict[str, Any]:
        """Process natural language query and return response"""
        
        if not self.enabled:
            return {
                "success": False,
                "error": "BigQuery integration is not enabled"
            }
        
        try:
            # 1. Get available schemas from Supabase
            schemas = await self.schema_manager.get_available_schemas(self.dataset_id)
            
            if not schemas:
                return {
                    "success": False,
                    "error": "No schemas found. Please refresh schemas from admin interface."
                }
            
            # 2. Ask AI to understand intent and generate SQL
            sql_response = await self._generate_sql(user_query, schemas, language)
            
            if not sql_response.get("success"):
                return sql_response
            
            generated_sql = sql_response["sql"]
            
            # 3. Validate SQL for safety
            if not self._validate_sql(generated_sql):
                return {
                    "success": False,
                    "error": "Generated SQL contains forbidden operations"
                }
            
            # 4. Execute the SQL
            query_result = await self._execute_bigquery(generated_sql)
            
            if not query_result.get("success"):
                return query_result
            
            # 5. Ask AI to create natural response
            final_response = await self._format_response(
                user_query, 
                query_result["data"], 
                language
            )
            
            # 6. Log the query
            await self._log_query(
                user_query=user_query,
                generated_sql=generated_sql,
                rows_returned=len(query_result["data"]),
                success=True,
                execution_time_ms=query_result.get("execution_time_ms", 0)
            )
            
            return {
                "success": True,
                "response": final_response,
                "metadata": {
                    "sql": generated_sql,
                    "rows": len(query_result["data"]),
                    "execution_time_ms": query_result.get("execution_time_ms", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_sql(self, user_query: str, schemas: List[Dict], language: str) -> Dict[str, Any]:
        """Generate SQL from natural language query"""
        try:
            # Format schemas for prompt
            schema_text = self._format_schemas(schemas)
            
            prompt = f"""
You are a BigQuery SQL expert. Generate a SQL query to answer the user's question.

User Query: {user_query}

Available Tables and Schemas:
{schema_text}

Generate a BigQuery SQL query to answer this question.
Return JSON with:
- sql: The SQL query (use fully qualified table names like `project.dataset.table`)
- explanation: Brief explanation of what the query does

Important:
- Use proper BigQuery syntax
- Include the project and dataset in table references: `{self.project_id}.{self.dataset_id}.table_name`
- Only use SELECT statements
- Limit results to {self.max_rows} rows maximum
- Use appropriate date functions for BigQuery
- Handle NULL values appropriately
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Add LIMIT if not present
            sql = result.get("sql", "")
            if "LIMIT" not in sql.upper():
                sql += f" LIMIT {self.max_rows}"
            
            return {
                "success": True,
                "sql": sql,
                "explanation": result.get("explanation", "")
            }
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to generate SQL: {str(e)}"
            }
    
    def _format_schemas(self, schemas: List[Dict]) -> str:
        """Format schemas for AI prompt"""
        formatted_schemas = []
        
        for schema in schemas:
            table_info = f"Table: {schema['table_id']}"
            if schema.get('table_description'):
                table_info += f" - {schema['table_description']}"
            
            columns = schema.get('columns_info', [])
            column_info = []
            
            for col in columns:
                col_desc = f"  - {col['name']} ({col['type']})"
                if col.get('description'):
                    col_desc += f" - {col['description']}"
                column_info.append(col_desc)
            
            formatted_schemas.append(f"{table_info}\n" + "\n".join(column_info))
        
        return "\n\n".join(formatted_schemas)
    
    def _validate_sql(self, sql: str) -> bool:
        """Basic SQL safety validation"""
        forbidden = ['DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
        sql_upper = sql.upper()
        
        for word in forbidden:
            if re.search(r'\b' + word + r'\b', sql_upper):
                return False
        
        return True
    
    async def _execute_bigquery(self, sql: str) -> Dict[str, Any]:
        """Execute BigQuery SQL"""
        try:
            start_time = datetime.now()
            
            # Configure query job
            job_config = bigquery.QueryJobConfig(
                use_legacy_sql=False,
                timeout_ms=self.timeout_seconds * 1000
            )
            
            # Run query
            query_job = self.bigquery_client.query(sql, job_config=job_config)
            results = query_job.result()
            
            # Convert to list of dicts
            data = []
            for row in results:
                data.append(dict(row))
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return {
                "success": True,
                "data": data,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"Error executing BigQuery: {str(e)}")
            return {
                "success": False,
                "error": f"Query execution failed: {str(e)}"
            }
    
    async def _format_response(self, user_query: str, query_results: List[Dict], language: str) -> str:
        """Format query results as natural language response"""
        try:
            # Detect language if auto
            if language == "auto":
                language = await self._detect_language(user_query)
            
            # Limit data for prompt to avoid token limits
            sample_data = query_results[:20] if len(query_results) > 20 else query_results
            
            prompt = f"""
User Question: {user_query}
Query Results: {json.dumps(sample_data, ensure_ascii=False, default=str)}
Total Rows: {len(query_results)}

Provide a helpful, natural response in {language if language != 'auto' else 'the same language as the question'}.
Format numbers appropriately for the language and region.
If there are many results, summarize the key findings.
Be concise but informative.
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return f"Query executed successfully. Found {len(query_results)} results."
    
    async def _detect_language(self, text: str) -> str:
        """Detect language of the query"""
        try:
            prompt = f"""
Detect the language of this text: "{text}"
Respond with just the language name (e.g., "Korean", "English", "Japanese")
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception:
            return "English"  # Default fallback
    
    async def _log_query(self, user_query: str, generated_sql: str, 
                        rows_returned: int, success: bool, 
                        execution_time_ms: int, error_message: str = None):
        """Log query to Supabase"""
        try:
            query_data = {
                'user_query': user_query,
                'generated_sql': generated_sql,
                'rows_returned': rows_returned,
                'success': success,
                'execution_time_ms': execution_time_ms,
                'error_message': error_message,
                'created_at': datetime.now().isoformat()
            }
            
            self.supabase.client.table('bigquery_queries').insert(query_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging query: {str(e)}")
    
    async def is_data_query(self, message: str) -> bool:
        """Determine if a message is asking for data from BigQuery"""
        
        if not self.enabled:
            return False
        
        try:
            # Get available schemas
            schemas = await self.schema_manager.get_available_schemas(self.dataset_id)
            
            if not schemas:
                return False
            
            # Create a list of table names
            table_names = [schema['table_id'] for schema in schemas]
            
            prompt = f"""
Is this question asking about data that would be in a database?
Consider these available tables: {', '.join(table_names)}

Question: {message}

Answer with just 'yes' or 'no'.
Examples that would be 'yes':
- "Show me sales data"
- "What's the revenue last month?"
- "김영수씨의 실적을 보여주세요"
- "How many customers do we have?"

Examples that would be 'no':
- "What is RAG?"
- "How do I upload a document?"
- "Explain the company policy"
- "What's in the uploaded PDF?"
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            return "yes" in response.choices[0].message.content.lower()
            
        except Exception as e:
            logger.error(f"Error checking if data query: {str(e)}")
            return False