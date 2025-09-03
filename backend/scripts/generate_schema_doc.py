#!/usr/bin/env python3
"""
Generate a schema document for BigQuery tables
Upload this to your assistant for better query generation
"""

from google.cloud import bigquery
import os
from dotenv import load_dotenv

load_dotenv('../.env')

def generate_schema_document():
    """Generate a document describing all BigQuery tables and schemas"""
    
    # Initialize BigQuery client
    client = bigquery.Client(project=os.getenv('GCP_PROJECT_ID'))
    dataset_id = os.getenv('BIGQUERY_DATASET', 'your_dataset')
    
    schema_doc = []
    schema_doc.append("# BigQuery Database Schema Reference")
    schema_doc.append("\nThis document contains the schema for all available BigQuery tables.")
    schema_doc.append("Use this reference when writing SQL queries.\n")
    
    try:
        # List all tables
        tables = client.list_tables(dataset_id)
        
        for table in tables:
            table_ref = client.get_table(f"{dataset_id}.{table.table_id}")
            
            schema_doc.append(f"\n## Table: {table.table_id}")
            schema_doc.append(f"Description: {table_ref.description or 'No description'}")
            schema_doc.append(f"Row count: {table_ref.num_rows}")
            schema_doc.append("\nColumns:")
            
            # List all columns with types
            for field in table_ref.schema:
                nullable = "NULL" if field.mode != "REQUIRED" else "NOT NULL"
                schema_doc.append(f"  - {field.name} ({field.field_type}) {nullable}")
                if field.description:
                    schema_doc.append(f"    Description: {field.description}")
            
            # Add sample queries
            schema_doc.append(f"\nSample queries:")
            schema_doc.append(f"  - SELECT * FROM {table.table_id} LIMIT 10")
            schema_doc.append(f"  - SELECT COUNT(*) FROM {table.table_id}")
            
            # Add common filters if known
            if 'date' in [f.name.lower() for f in table_ref.schema]:
                schema_doc.append(f"  - SELECT * FROM {table.table_id} WHERE date >= '2024-01-01'")
        
        # Add query tips
        schema_doc.append("\n## Query Writing Tips")
        schema_doc.append("- Always use proper date format: 'YYYY-MM-DD'")
        schema_doc.append("- For Korean text, use LIKE '%검색어%' for searching")
        schema_doc.append("- Use LIMIT to avoid large result sets")
        schema_doc.append("- Join tables using appropriate foreign keys")
        
        # Save to file
        output_file = "bigquery_schema_reference.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(schema_doc))
        
        print(f"✅ Schema document generated: {output_file}")
        print("📤 Upload this file to your assistant for better query generation!")
        
        return '\n'.join(schema_doc)
        
    except Exception as e:
        print(f"❌ Error generating schema: {e}")
        return None

if __name__ == "__main__":
    generate_schema_document()