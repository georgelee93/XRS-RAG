"""
BigQuery Integration for OpenAI Assistant v2
Enables querying BigQuery tables through function calling
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime

logger = logging.getLogger(__name__)


class BigQueryClient:
    """BigQuery client for executing queries"""
    
    def __init__(self):
        """Initialize BigQuery client with service account"""
        self.client = None
        self.project_id = None
        self.dataset_id = os.getenv("BIGQUERY_DATASET", "ca_stats")  # Use ca_stats dataset
        
        # Try to initialize from service account key or default credentials
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if key_path and os.path.exists(key_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(key_path)
                self.client = bigquery.Client(credentials=credentials)
                self.project_id = credentials.project_id
                logger.info(f"BigQuery client initialized with service account for project: {self.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize BigQuery with service account: {e}")
        else:
            # Try to use default application credentials (gcloud auth)
            try:
                self.client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID", "ca-stats-455623"))
                self.project_id = self.client.project
                logger.info(f"BigQuery client initialized with default credentials for project: {self.project_id}")
            except Exception as e:
                logger.warning(f"BigQuery credentials not available: {e}")
    
    def is_available(self) -> bool:
        """Check if BigQuery client is available"""
        return self.client is not None
    
    async def execute_query(self, query: str, max_results: int = 100) -> Dict[str, Any]:
        """Execute a BigQuery SQL query"""
        if not self.client:
            return {
                "error": "BigQuery not configured",
                "message": "Please configure BigQuery credentials"
            }
        
        try:
            logger.info(f"Executing query: {query[:100]}...")
            
            # Execute query
            query_job = self.client.query(query)
            results = query_job.result()
            
            # Convert to list of dicts
            rows = []
            for row in results:
                rows.append(dict(row))
                if len(rows) >= max_results:
                    break
            
            return {
                "success": True,
                "data": rows,
                "row_count": len(rows),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a table"""
        if not self.client:
            return {"error": "BigQuery not configured"}
        
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"
            table = self.client.get_table(table_ref)
            
            schema = []
            for field in table.schema:
                schema.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description
                })
            
            return {
                "table_name": table_name,
                "schema": schema,
                "row_count": table.num_rows,
                "size_mb": table.num_bytes / (1024 * 1024) if table.num_bytes else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return {"error": str(e)}
    
    async def list_tables_with_details(self) -> List[Dict[str, Any]]:
        """List all tables with detailed information"""
        if not self.client:
            return []
        
        tables_info = []
        try:
            # List all datasets
            datasets = list(self.client.list_datasets())
            
            for dataset in datasets:
                dataset_id = dataset.dataset_id
                tables = list(self.client.list_tables(dataset.reference))
                
                for table in tables:
                    try:
                        # Get table details
                        table_ref = f"{self.project_id}.{dataset_id}.{table.table_id}"
                        table_obj = self.client.get_table(table_ref)
                        
                        # Get schema info
                        schema_fields = []
                        for field in table_obj.schema[:10]:  # First 10 fields
                            schema_fields.append({
                                "name": field.name,
                                "type": field.field_type,
                                "mode": field.mode
                            })
                        
                        tables_info.append({
                            "dataset_id": dataset_id,
                            "table_id": table.table_id,
                            "table_name": f"{dataset_id}.{table.table_id}",
                            "full_table_id": table_ref,
                            "description": table_obj.description or f"Table in {dataset_id} dataset",
                            "row_count": table_obj.num_rows,
                            "size_mb": round(table_obj.num_bytes / (1024 * 1024), 2) if table_obj.num_bytes else 0,
                            "created": table_obj.created.isoformat() if table_obj.created else None,
                            "modified": table_obj.modified.isoformat() if table_obj.modified else None,
                            "schema": schema_fields,
                            "column_count": len(table_obj.schema)
                        })
                    except Exception as e:
                        logger.warning(f"Could not get details for table {table.table_id}: {e}")
                        tables_info.append({
                            "dataset_id": dataset_id,
                            "table_id": table.table_id,
                            "table_name": f"{dataset_id}.{table.table_id}",
                            "description": "Table information unavailable",
                            "row_count": 0,
                            "column_count": 0
                        })
            
            return tables_info
            
        except Exception as e:
            logger.error(f"Failed to list tables with details: {e}")
            return []
    
    async def list_tables(self) -> List[str]:
        """List all available tables"""
        if not self.client:
            return []
        
        try:
            # Try to list tables from the configured dataset
            dataset_ref = f"{self.project_id}.{self.dataset_id}"
            dataset = self.client.get_dataset(dataset_ref)
            tables = list(self.client.list_tables(dataset))
            return [f"{self.dataset_id}.{table.table_id}" for table in tables]
        except Exception as e:
            logger.warning(f"Dataset {self.dataset_id} not found, listing all datasets")
            try:
                # List all datasets and their tables
                all_tables = []
                datasets = list(self.client.list_datasets())
                for dataset in datasets:
                    tables = list(self.client.list_tables(dataset.reference))
                    for table in tables:
                        all_tables.append(f"{dataset.dataset_id}.{table.table_id}")
                return all_tables
            except Exception as e2:
                logger.error(f"Failed to list tables: {e2}")
                return []
    
    def generate_sales_query(self, period: str, metric: str = "sales") -> str:
        """Generate a sales query based on period"""
        # Map common period names to SQL
        period_lower = period.lower()
        
        # Current year assumed
        current_year = datetime.now().year
        
        if "august" in period_lower or "8월" in period_lower:
            date_filter = f"DATE(date) BETWEEN '{current_year}-08-01' AND '{current_year}-08-31'"
        elif "july" in period_lower or "7월" in period_lower:
            date_filter = f"DATE(date) BETWEEN '{current_year}-07-01' AND '{current_year}-07-31'"
        elif "june" in period_lower or "6월" in period_lower:
            date_filter = f"DATE(date) BETWEEN '{current_year}-06-01' AND '{current_year}-06-30'"
        elif "this month" in period_lower or "이번달" in period_lower:
            date_filter = f"DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)"
        elif "last month" in period_lower or "지난달" in period_lower:
            date_filter = f"DATE(date) BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH) AND LAST_DAY(DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 DAY))"
        else:
            # Default to current month
            date_filter = f"DATE(date) >= DATE_TRUNC(CURRENT_DATE(), MONTH)"
        
        # Generate query (adjust table and column names as needed)
        query = f"""
        SELECT 
            DATE(date) as date,
            SUM(amount) as total_{metric},
            COUNT(*) as transaction_count
        FROM `{self.project_id}.{self.dataset_id}.sales_table`
        WHERE {date_filter}
        GROUP BY date
        ORDER BY date DESC
        """
        
        return query.strip()


# Singleton instance
_bq_client: Optional[BigQueryClient] = None


def get_bigquery_client() -> BigQueryClient:
    """Get or create BigQuery client"""
    global _bq_client
    if _bq_client is None:
        _bq_client = BigQueryClient()
    return _bq_client