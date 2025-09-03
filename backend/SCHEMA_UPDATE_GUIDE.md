# BigQuery Schema Update Guide

## Quick Process

### 1. Initial Setup (One Time)
```bash
# Generate schema document
cd backend/scripts
python3 generate_schema_doc.py

# Upload to assistant (through your admin panel)
Upload: bigquery_schema_reference.txt
```

### 2. When Schema Changes
```bash
# Option A: Manual Update
1. Edit bigquery_schema_reference.txt
2. Re-upload to assistant (replaces old version)

# Option B: Auto-generate
1. Run generate_schema_doc.py again
2. Upload new version
```

### 3. What to Include in Schema Doc

```text
# BIGQUERY SCHEMA REFERENCE
# Updated: 2024-03-14

## Table: customers
Columns:
- id (INTEGER) - Customer ID
- name (STRING) - Customer name  
- email (STRING) - Email address
- created_at (TIMESTAMP) - Registration date
- tier (STRING) - Customer tier (gold/silver/bronze)

## Table: sales  
Columns:
- id (INTEGER) - Transaction ID
- customer_id (INTEGER) - Links to customers.id
- amount (FLOAT) - Sale amount in KRW
- date (DATE) - Transaction date
- product_id (STRING) - Product code

## Common Queries
- Monthly revenue: SELECT DATE_TRUNC(date, MONTH) as month, SUM(amount) FROM sales GROUP BY 1
- Customer totals: SELECT c.name, SUM(s.amount) FROM sales s JOIN customers c ON s.customer_id = c.id GROUP BY 1
- Recent sales: SELECT * FROM sales WHERE date >= CURRENT_DATE() - 30 ORDER BY date DESC
```

### 4. Pro Tips

✅ **DO:**
- Include sample queries for common questions
- Document foreign key relationships
- Add data type for each column
- Include any special formatting rules

❌ **DON'T:**
- Include sensitive information (passwords, keys)
- Put actual data values (just structure)
- Make it too verbose (keep it scannable)

### 5. Automation Option

Add to your CI/CD:
```yaml
# When database migrations run:
1. Run migration
2. Generate new schema doc
3. Upload to OpenAI via API
4. Notify team of update
```