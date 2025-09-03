# BigQuery Integration with OpenAI Assistant API v2

## Overview
The chatbot now supports BigQuery function calling, allowing it to query your data warehouse for analytics and business metrics.

## How It Works

1. **User asks a data question**: "What were the sales for August?"
2. **Assistant recognizes it needs data** and calls the `query_bigquery` function
3. **Backend executes the query** on BigQuery
4. **Results are returned** to the Assistant
5. **Assistant formats the response** in natural language

## Available Functions

### 1. `query_bigquery(query: string)`
Executes a SQL query on BigQuery and returns results.

Example:
```sql
SELECT SUM(amount) as total_sales 
FROM sales_table 
WHERE DATE(date) BETWEEN '2024-08-01' AND '2024-08-31'
```

### 2. `list_bigquery_tables()`
Lists all available tables in BigQuery.

## Setup

### 1. Set Environment Variables
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
export BIGQUERY_DATASET="your_dataset_name"  # Optional, defaults to "analytics"
```

### 2. Service Account Permissions
Your service account needs:
- `bigquery.dataViewer` - To read data
- `bigquery.jobUser` - To run queries

### 3. Upload Schema Documentation
For best results, upload a document describing your BigQuery tables:

```markdown
## BigQuery Schema

### sales_table
- date (DATE): Transaction date
- amount (FLOAT): Sale amount in USD
- product_id (STRING): Product identifier
- customer_id (STRING): Customer ID

### inventory_table
- product_id (STRING): Product ID
- quantity (INTEGER): Stock quantity
- warehouse_id (STRING): Warehouse location
```

## Example Queries

### Sales Questions
- "What were the total sales for August?"
- "Show me revenue by product for last month"
- "What are the top 10 customers by sales?"

### Inventory Questions
- "What's the current inventory level?"
- "Which products are low in stock?"
- "Show warehouse inventory distribution"

## Testing

Test the integration:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List available BigQuery tables"}'
```

## Current Status

✅ **Implemented:**
- Function calling integrated with Assistant API v2
- Query execution with error handling
- Table listing and discovery
- Results formatting

⚠️ **Configuration Needed:**
1. Create BigQuery dataset with your data
2. Update `BIGQUERY_DATASET` environment variable
3. Upload schema documentation for better query generation

## Cost Considerations

- **BigQuery costs**: ~$5 per TB scanned
- **OpenAI costs**: Additional tokens for function calls
- **Recommendation**: Use partitioned tables and limit query scope

## Troubleshooting

### "Dataset not found"
- Check that your dataset exists in BigQuery
- Verify service account has access
- Update `BIGQUERY_DATASET` environment variable

### "No tables found"
- Ensure tables exist in your dataset
- Check service account permissions
- Try listing all datasets first

### Query errors
- Upload schema documentation
- Provide example queries in prompts
- Check SQL syntax for BigQuery compatibility