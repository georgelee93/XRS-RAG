"""
BigQuery Integration Module
Provides live data access to complement static document retrieval
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False
try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    BIGQUERY_AVAILABLE = True
except ImportError:
    bigquery = None
    service_account = None
    BIGQUERY_AVAILABLE = False
import time

from .utils import get_env_var, create_error_response


logger = logging.getLogger(__name__)


class BigQueryRAGIntegration:
    """Integrates BigQuery live data with RAG system"""
    
    def __init__(self, credentials_path: Optional[str] = None, project_id: Optional[str] = None):
        """Initialize BigQuery client"""
        try:
            # Get credentials
            creds_path = credentials_path or get_env_var("GOOGLE_APPLICATION_CREDENTIALS", required=False)
            self.project_id = project_id or get_env_var("GCP_PROJECT_ID", required=False)
            
            if creds_path and os.path.exists(creds_path):
                # Use explicit credentials file if available
                self.credentials = service_account.Credentials.from_service_account_file(creds_path)
                self.client = bigquery.Client(
                    credentials=self.credentials,
                    project=self.project_id
                )
                self.enabled = True
                logger.info("BigQuery integration initialized with service account file")
            elif self.project_id:
                # Try using default application credentials (for Cloud Run, GKE, etc.)
                try:
                    self.client = bigquery.Client(project=self.project_id)
                    self.enabled = True
                    logger.info("BigQuery integration initialized with default credentials")
                except Exception as e:
                    logger.warning(f"Could not initialize with default credentials: {e}")
                    self.client = None
                    self.enabled = False
            else:
                self.client = None
                self.enabled = False
                logger.warning("BigQuery integration disabled - no project ID configured")
                
            self.query_templates = self._load_query_templates()
            self.query_cache = {}
            self.cache_ttl = 300  # 5 minutes
            
        except Exception as e:
            logger.error(f"Error initializing BigQuery: {str(e)}")
            self.enabled = False
    
    def _load_query_templates(self) -> Dict[str, str]:
        """Pre-defined query templates for common questions"""
        return {
            'inventory_status': """
                SELECT 
                    item_id, 
                    item_name,
                    current_stock, 
                    reorder_level,
                    CASE 
                        WHEN current_stock < reorder_level THEN 'REORDER_NEEDED'
                        WHEN current_stock < reorder_level * 1.5 THEN 'LOW_STOCK'
                        ELSE 'OK'
                    END as status
                FROM `{project}.{dataset}.inventory`
                WHERE item_name LIKE @item_filter
                ORDER BY current_stock ASC
                LIMIT 20
            """,
            'sales_summary': """
                SELECT 
                    DATE(timestamp) as sale_date,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_sales,
                    AVG(amount) as avg_transaction
                FROM `{project}.{dataset}.sales`
                WHERE timestamp >= @start_date
                    AND timestamp <= @end_date
                GROUP BY sale_date
                ORDER BY sale_date DESC
            """,
            'customer_info': """
                SELECT 
                    customer_id,
                    customer_name,
                    last_order_date,
                    total_orders,
                    lifetime_value
                FROM `{project}.{dataset}.customers`
                WHERE customer_id = @customer_id
                    OR customer_name LIKE @customer_name
            """,
            'performance_metrics': """
                SELECT 
                    metric_name,
                    metric_value,
                    timestamp,
                    category
                FROM `{project}.{dataset}.metrics`
                WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
                ORDER BY timestamp DESC
            """,
            'product_analytics': """
                SELECT 
                    product_id,
                    product_name,
                    views,
                    clicks,
                    conversions,
                    SAFE_DIVIDE(conversions, views) * 100 as conversion_rate
                FROM `{project}.{dataset}.product_analytics`
                WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
                ORDER BY conversion_rate DESC
                LIMIT 50
            """
        }
    
    def extract_query_intent(self, user_question: str) -> Dict[str, Any]:
        """Analyze user question to determine query type and parameters"""
        if not self.enabled:
            return {'query_type': None, 'params': {}}
            
        question_lower = user_question.lower()
        
        # Inventory queries
        if any(word in question_lower for word in ['inventory', 'stock', 'reorder', 'items']):
            item_filter = '%'
            # Extract specific item if mentioned
            if 'item' in question_lower:
                words = question_lower.split()
                item_idx = words.index('item')
                if item_idx + 1 < len(words):
                    item_filter = f'%{words[item_idx + 1]}%'
            
            return {
                'query_type': 'inventory_status',
                'params': {'item_filter': item_filter}
            }
        
        # Sales queries
        elif any(word in question_lower for word in ['sales', 'revenue', 'transactions']):
            # Default to last 30 days
            days = 30
            if 'week' in question_lower:
                days = 7
            elif 'month' in question_lower:
                days = 30
            elif 'year' in question_lower:
                days = 365
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            return {
                'query_type': 'sales_summary',
                'params': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }
            }
        
        # Customer queries
        elif any(word in question_lower for word in ['customer', 'client', 'user']):
            return {
                'query_type': 'customer_info',
                'params': {
                    'customer_name': '%',
                    'customer_id': ''
                }
            }
        
        # Performance metrics
        elif any(word in question_lower for word in ['performance', 'metrics', 'kpi']):
            hours = 24  # Default to last 24 hours
            if 'hour' in question_lower:
                hours = 1
            elif 'day' in question_lower:
                hours = 24
            elif 'week' in question_lower:
                hours = 168
                
            return {
                'query_type': 'performance_metrics',
                'params': {'hours': hours}
            }
        
        # Product analytics
        elif any(word in question_lower for word in ['product', 'conversion', 'analytics']):
            days = 7  # Default to last week
            if 'month' in question_lower:
                days = 30
            elif 'year' in question_lower:
                days = 365
                
            return {
                'query_type': 'product_analytics',
                'params': {'days': days}
            }
        
        return {'query_type': None, 'params': {}}
    
    def execute_query(self, query_type: str, params: Dict[str, Any], 
                     dataset: str = None):
        """Execute BigQuery with parameters"""
        if not self.enabled:
            raise ValueError("BigQuery integration is not enabled")
            
        if query_type not in self.query_templates:
            raise ValueError(f"Unknown query type: {query_type}")
        
        dataset = dataset or get_env_var("BIGQUERY_DATASET", default="default_dataset")
        
        # Format query with project and dataset
        query = self.query_templates[query_type].format(
            project=self.project_id,
            dataset=dataset
        )
        
        # Sanitize parameters
        params = self.sanitize_params(params)
        
        # Configure query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                self._create_query_parameter(k, v)
                for k, v in params.items()
            ]
        )
        
        try:
            # Execute query
            query_job = self.client.query(query, job_config=job_config)
            
            # Wait for results with timeout
            results = query_job.result(timeout=30)
            
            # Convert to DataFrame
            df = results.to_dataframe()
            
            logger.info(f"Query executed successfully: {query_type}, rows returned: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"BigQuery execution error: {str(e)}")
            raise
    
    def get_live_context(self, user_question: str, use_cache: bool = True) -> Dict[str, Any]:
        """Main method to get live data context for RAG"""
        if not self.enabled:
            return {
                'has_data': False,
                'message': 'BigQuery integration not configured'
            }
            
        try:
            # Extract intent from question
            intent = self.extract_query_intent(user_question)
            
            if not intent['query_type']:
                return {
                    'has_data': False,
                    'message': 'No live data query needed for this question'
                }
            
            # Check cache if enabled
            if use_cache:
                cache_key = self._generate_cache_key(intent)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    logger.info(f"Returning cached result for query type: {intent['query_type']}")
                    return cached_result
            
            # Execute query
            df = self.execute_query(intent['query_type'], intent['params'])
            
            # Format result
            result = {
                'has_data': True,
                'query_type': intent['query_type'],
                'row_count': len(df),
                'data': df.to_dict('records') if len(df) <= 100 else df.head(100).to_dict('records'),
                'summary': self._generate_data_summary(df, intent['query_type']),
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache result
            if use_cache:
                self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"BigQuery error: {str(e)}")
            return {
                'has_data': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to prevent SQL injection"""
        sanitized = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Remove potentially dangerous characters
                value = value.replace(';', '').replace('--', '').replace('/*', '').replace('*/', '')
                # Limit length
                value = value[:100]
            sanitized[key] = value
            
        return sanitized
    
    def _create_query_parameter(self, name: str, value: Any):
        """Create BigQuery query parameter with appropriate type"""
        if isinstance(value, str):
            return bigquery.ScalarQueryParameter(name, "STRING", value)
        elif isinstance(value, int):
            return bigquery.ScalarQueryParameter(name, "INT64", value)
        elif isinstance(value, float):
            return bigquery.ScalarQueryParameter(name, "FLOAT64", value)
        elif isinstance(value, bool):
            return bigquery.ScalarQueryParameter(name, "BOOL", value)
        elif isinstance(value, datetime):
            return bigquery.ScalarQueryParameter(name, "TIMESTAMP", value)
        else:
            # Convert to string as fallback
            return bigquery.ScalarQueryParameter(name, "STRING", str(value))
    
    def _generate_data_summary(self, df, query_type: str) -> str:
        """Generate a text summary of the data"""
        if df.empty:
            return "No data found matching the criteria"
        
        summary = f"Found {len(df)} records. "
        
        # Query-specific summaries
        if query_type == 'inventory_status':
            if 'status' in df.columns:
                status_counts = df['status'].value_counts()
                if 'REORDER_NEEDED' in status_counts:
                    summary += f"{status_counts['REORDER_NEEDED']} items need reordering. "
                if 'LOW_STOCK' in status_counts:
                    summary += f"{status_counts['LOW_STOCK']} items have low stock. "
        
        elif query_type == 'sales_summary':
            if 'total_sales' in df.columns:
                total = df['total_sales'].sum()
                avg = df['total_sales'].mean()
                summary += f"Total sales: ${total:,.2f}, Average daily: ${avg:,.2f}"
        
        elif query_type == 'product_analytics':
            if 'conversion_rate' in df.columns:
                avg_conversion = df['conversion_rate'].mean()
                summary += f"Average conversion rate: {avg_conversion:.2f}%"
        
        return summary
    
    def _generate_cache_key(self, intent: Dict[str, Any]) -> str:
        """Generate cache key from query intent"""
        key_parts = [intent['query_type']]
        for k, v in sorted(intent['params'].items()):
            key_parts.append(f"{k}:{v}")
        return "|".join(key_parts)
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached query result if available and not expired"""
        if cache_key in self.query_cache:
            cached_data, timestamp = self.query_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            else:
                # Remove expired entry
                del self.query_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache query result"""
        self.query_cache[cache_key] = (result, time.time())
        
        # Clean old cache entries if cache grows too large
        if len(self.query_cache) > 100:
            self._clean_cache()
    
    def _clean_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.query_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.query_cache[key]
    
    def test_connection(self) -> bool:
        """Test BigQuery connection"""
        if not self.enabled:
            return False
            
        try:
            # Simple query to test connection
            query = "SELECT 1 as test"
            query_job = self.client.query(query)
            list(query_job.result())
            logger.info("BigQuery connection test successful")
            return True
        except Exception as e:
            logger.error(f"BigQuery connection test failed: {str(e)}")
            return False