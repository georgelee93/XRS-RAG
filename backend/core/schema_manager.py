"""
Schema Manager for BigQuery Integration
Manages schema storage and retrieval from Supabase
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .supabase_client import get_supabase_manager

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages BigQuery schemas in Supabase"""
    
    def __init__(self):
        self.supabase = get_supabase_manager()
    
    async def store_schemas(self, schemas: Dict[str, Any], dataset_id: str, project_id: str):
        """Store discovered schemas in Supabase"""
        try:
            for table_id, schema_info in schemas.items():
                schema_data = {
                    'table_id': table_id,
                    'dataset_id': dataset_id,
                    'project_id': project_id,
                    'table_name': schema_info.get('table_name', table_id),
                    'table_description': schema_info.get('description', ''),
                    'schema_json': schema_info,
                    'columns_info': schema_info.get('columns', []),
                    'last_updated': datetime.now().isoformat(),
                    'is_active': True
                }
                
                # Upsert schema
                result = self.supabase.client.table('bigquery_schemas').upsert(
                    schema_data,
                    on_conflict='table_id,dataset_id'
                ).execute()
                
                logger.info(f"Stored schema for table {table_id}")
                
        except Exception as e:
            logger.error(f"Error storing schemas: {str(e)}")
    
    async def get_available_schemas(self, dataset_id: str = None) -> List[Dict[str, Any]]:
        """Get available schemas from Supabase"""
        try:
            query = self.supabase.client.table('bigquery_schemas').select('*')
            
            if dataset_id:
                query = query.eq('dataset_id', dataset_id)
            
            query = query.eq('is_active', True)
            result = query.execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting schemas: {str(e)}")
            return []
    
    async def get_table_schema(self, table_id: str, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get specific table schema"""
        try:
            result = self.supabase.client.table('bigquery_schemas').select('*').eq(
                'table_id', table_id
            ).eq('dataset_id', dataset_id).eq('is_active', True).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting table schema: {str(e)}")
            return None
    
    async def log_schema_change(self, table_id: str, dataset_id: str, change_type: str, 
                               old_schema: Dict = None, new_schema: Dict = None, 
                               change_details: Dict = None):
        """Log schema changes for monitoring"""
        try:
            change_data = {
                'table_id': table_id,
                'dataset_id': dataset_id,
                'change_type': change_type,
                'old_schema': old_schema,
                'new_schema': new_schema,
                'change_details': change_details or {},
                'detected_at': datetime.now().isoformat(),
                'processed': False
            }
            
            result = self.supabase.client.table('schema_change_log').insert(change_data).execute()
            logger.info(f"Logged schema change: {change_type} for table {table_id}")
            
        except Exception as e:
            logger.error(f"Error logging schema change: {str(e)}")
    
    async def get_recent_schema_changes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent schema changes"""
        try:
            result = self.supabase.client.table('schema_change_log').select('*').order(
                'detected_at', desc=True
            ).limit(limit).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting schema changes: {str(e)}")
            return []