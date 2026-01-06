#!/usr/bin/env python3
"""Check the SEC database schema to understand table structure."""

import os
import sys

# Parse export_variables file
def load_env_from_file(filepath):
    env = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('export ') and '=' in line:
                line = line[7:]
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                env[key] = value
    return env

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
env_file = os.path.join(project_dir, 'export_variables')
env = load_env_from_file(env_file)

import snowflake.connector

conn = snowflake.connector.connect(
    account=env['SNOWFLAKE_ACCOUNT'],
    user=env['SNOWFLAKE_USER'],
    password=env['SNOWFLAKE_PASSWORD'],
    warehouse=env['SNOWFLAKE_WAREHOUSE'],
    role=env['SNOWFLAKE_ROLE'],
)

cursor = conn.cursor()

print("=" * 60)
print("Checking SEC_FILINGS_DEMO_DATA.CYBERSYN schema")
print("=" * 60)

# List all tables
print("\n1. ALL Tables in CYBERSYN schema:")
cursor.execute("SHOW TABLES IN SEC_FILINGS_DEMO_DATA.CYBERSYN")
for row in cursor.fetchall():
    print(f"   - {row[1]}")

# List all views
print("\n2. ALL Views in CYBERSYN schema:")
cursor.execute("SHOW VIEWS IN SEC_FILINGS_DEMO_DATA.CYBERSYN")
for row in cursor.fetchall():
    print(f"   - {row[1]}")

# Check data dictionary
print("\n3. Data Dictionary (if exists):")
try:
    cursor.execute("SELECT * FROM SEC_FILINGS_DEMO_DATA.CYBERSYN.CYBERSYN_DATA_DICTIONARY LIMIT 20")
    for row in cursor.fetchall():
        print(f"   {row}")
except Exception as e:
    print(f"   Error: {e}")

# Sample companies from SEC_CIK_INDEX
print("\n4. Sample data from SEC_CIK_INDEX (first few columns):")
cursor.execute("""
    SELECT CIK, COMPANY_NAME, SIC, SIC_CODE_DESCRIPTION
    FROM SEC_FILINGS_DEMO_DATA.CYBERSYN.SEC_CIK_INDEX
    WHERE COMPANY_NAME ILIKE '%APPLE%'
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"   {row}")

# Check for Company Index or ticker mapping table
print("\n5. Looking for ticker/company mapping:")
try:
    cursor.execute("DESCRIBE TABLE SEC_FILINGS_DEMO_DATA.CYBERSYN.COMPANY_INDEX")
    print("   COMPANY_INDEX columns:")
    for row in cursor.fetchall():
        print(f"     - {row[0]}: {row[1]}")
except Exception as e:
    print(f"   COMPANY_INDEX not found: {e}")

# Sample 10-K filing
print("\n6. Sample 10-K filing data:")
cursor.execute("""
    SELECT txt.CIK, txt.ADSH, txt.SEC_DOCUMENT_ID, txt.VARIABLE_NAME, txt.PERIOD_END_DATE, LENGTH(txt.VALUE) as text_len
    FROM SEC_FILINGS_DEMO_DATA.CYBERSYN.SEC_REPORT_TEXT_ATTRIBUTES txt
    WHERE txt.VARIABLE_NAME = '10-K Filing Text'
    ORDER BY txt.PERIOD_END_DATE DESC
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"   {row}")

# Get a specific company by CIK
print("\n7. Apple's CIK and filings (CIK 0000320193):")
cursor.execute("""
    SELECT CIK, COMPANY_NAME
    FROM SEC_FILINGS_DEMO_DATA.CYBERSYN.SEC_CIK_INDEX
    WHERE CIK = '0000320193'
""")
for row in cursor.fetchall():
    print(f"   {row}")

cursor.close()
conn.close()
print("\nDone!")
