"""
BigQuery Schema Registry
Discovers and manages BigQuery table schemas
"""

import logging
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class BigQuerySchemaRegistry:
    """Manages BigQuery table schemas and metadata"""
    
    def __init__(self, credentials_path: str = None, project_id: str = None):
        """Initialize BigQuery client"""
        try:
            # Get credentials
            creds_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
            
            if creds_path and os.path.exists(creds_path):
                # Use service account file if available
                self.credentials = service_account.Credentials.from_service_account_file(creds_path)
                self.client = bigquery.Client(
                    credentials=self.credentials,
                    project=self.project_id
                )
                self.enabled = True
                logger.info("BigQuery Schema Registry initialized with service account file")
            elif self.project_id:
                # Use default application credentials (for Cloud Run)
                self.client = bigquery.Client(project=self.project_id)
                self.enabled = True
                logger.info("BigQuery Schema Registry initialized with default credentials")
            else:
                self.client = None
                self.enabled = False
                logger.warning("BigQuery Schema Registry disabled - no project ID specified")
                
        except Exception as e:
            logger.error(f"Error initializing BigQuery Schema Registry: {str(e)}")
            self.enabled = False
    
    async def discover_schemas(self, dataset_id: str) -> Dict[str, Any]:
        """Discover all tables and their schemas"""
        if not self.enabled:
            return {}
            
        try:
            dataset_ref = self.client.dataset(dataset_id, project=self.project_id)
            tables = list(self.client.list_tables(dataset_ref))
            
            schemas = {}
            for table in tables:
                table_ref = self.client.get_table(table)
                schema_info = self._extract_schema_info(table_ref)
                schemas[table.table_id] = schema_info
                
            logger.info(f"Discovered {len(schemas)} tables in dataset {dataset_id}")
            return schemas
            
        except Exception as e:
            logger.error(f"Error discovering schemas: {str(e)}")
            return {}
    
    def _extract_schema_info(self, table_ref) -> Dict[str, Any]:
        """Extract schema information from BigQuery table"""
        schema_info = {
            'table_id': table_ref.table_id,
            'dataset_id': table_ref.dataset_id,
            'project_id': table_ref.project,
            'table_name': table_ref.table_id,
            'description': table_ref.description or '',
            'columns': [],
            'row_count': table_ref.num_rows or 0,
            'size_bytes': table_ref.num_bytes or 0,
            'created': table_ref.created.isoformat() if table_ref.created else None,
            'modified': table_ref.modified.isoformat() if table_ref.modified else None
        }
        
        # Extract column information
        for field in table_ref.schema:
            column_info = {
                'name': field.name,
                'type': field.field_type,
                'mode': field.mode or 'NULLABLE',
                'description': field.description or ''
            }
            schema_info['columns'].append(column_info)
        
        return schema_info
    
    def test_connection(self) -> bool:
        """Test BigQuery connection"""
        if not self.enabled:
            return False
            
        try:
            # Try to list datasets
            datasets = list(self.client.list_datasets())
            logger.info(f"BigQuery connection successful. Found {len(datasets)} datasets.")
            return True
        except Exception as e:
            logger.error(f"BigQuery connection failed: {str(e)}")
            return False
    
    async def refresh_schemas(self, dataset_id: str) -> Dict[str, Any]:
        """Refresh schemas manually via admin interface"""
        if not self.enabled:
            return {'success': False, 'error': 'BigQuery not enabled'}
        
        try:
            # Get current schemas
            current_schemas = await self.discover_schemas(dataset_id)
            
            logger.info(f"Manual schema refresh completed for dataset {dataset_id}")
            return {
                'success': True,
                'schemas': current_schemas,
                'count': len(current_schemas),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error refreshing schemas: {str(e)}")
            return {'success': False, 'error': str(e)}