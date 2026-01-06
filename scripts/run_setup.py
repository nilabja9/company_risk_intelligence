#!/usr/bin/env python3
"""
Run the Snowflake setup script.
Reads credentials from export_variables file.
"""

import os
import sys
import re

# Parse export_variables file
def load_env_from_file(filepath):
    env = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('export ') and '=' in line:
                # Remove 'export ' prefix
                line = line[7:]
                key, value = line.split('=', 1)
                # Remove quotes from value
                value = value.strip('"\'')
                env[key] = value
    return env

def parse_sql_statements(sql_content):
    """Parse SQL file into individual statements, handling multi-line statements."""
    # Remove multi-line comments
    sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)

    statements = []
    current_stmt = []

    for line in sql_content.split('\n'):
        # Skip single-line comments
        stripped = line.strip()
        if stripped.startswith('--'):
            continue
        if not stripped:
            continue

        current_stmt.append(line)

        # Check if line ends with semicolon (end of statement)
        if stripped.endswith(';'):
            stmt = '\n'.join(current_stmt).strip()
            # Remove trailing semicolon for execution
            stmt = stmt.rstrip(';').strip()
            if stmt:
                statements.append(stmt)
            current_stmt = []

    # Don't forget last statement if no semicolon
    if current_stmt:
        stmt = '\n'.join(current_stmt).strip().rstrip(';').strip()
        if stmt:
            statements.append(stmt)

    return statements

# Load environment
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
env_file = os.path.join(project_dir, 'export_variables')

print(f"Loading credentials from: {env_file}")
env = load_env_from_file(env_file)

print(f"Account: {env.get('SNOWFLAKE_ACCOUNT')}")
print(f"User: {env.get('SNOWFLAKE_USER')}")
print(f"Warehouse: {env.get('SNOWFLAKE_WAREHOUSE')}")
print()

# Connect to Snowflake
try:
    import snowflake.connector
except ImportError:
    print("ERROR: snowflake-connector-python not installed")
    print("Run: pip install snowflake-connector-python")
    sys.exit(1)

print("Connecting to Snowflake...")
try:
    conn = snowflake.connector.connect(
        account=env['SNOWFLAKE_ACCOUNT'],
        user=env['SNOWFLAKE_USER'],
        password=env['SNOWFLAKE_PASSWORD'],
        warehouse=env['SNOWFLAKE_WAREHOUSE'],
        role=env['SNOWFLAKE_ROLE'],
    )
    print("Connected successfully!\n")
except Exception as e:
    print(f"ERROR connecting to Snowflake: {e}")
    sys.exit(1)

# Read and execute the setup script
sql_file = os.path.join(script_dir, 'setup_snowflake_tables.sql')
print(f"Reading SQL from: {sql_file}\n")

with open(sql_file, 'r') as f:
    sql_content = f.read()

# Parse statements
statements = parse_sql_statements(sql_content)
print(f"Found {len(statements)} SQL statements to execute\n")

# Execute each statement
cursor = conn.cursor()
success_count = 0
error_count = 0

for i, stmt in enumerate(statements, 1):
    # Get first line for display
    first_line = stmt.split('\n')[0].strip()
    if len(first_line) > 70:
        first_line = first_line[:70] + '...'

    print(f"[{i}/{len(statements)}] {first_line}")

    try:
        cursor.execute(stmt)
        result = cursor.fetchall()
        if result:
            if len(result) <= 10:
                for row in result:
                    # Format row output
                    row_str = str(row)
                    if len(row_str) > 100:
                        row_str = row_str[:100] + '...'
                    print(f"    {row_str}")
            else:
                print(f"    ... {len(result)} rows returned")
        success_count += 1
        print(f"    ✓ Success")
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 100:
            error_msg = error_msg[:100] + '...'
        print(f"    ✗ ERROR: {error_msg}")
        error_count += 1
    print()

cursor.close()
conn.close()

print("=" * 60)
print(f"Setup complete! {success_count} succeeded, {error_count} failed")
print("=" * 60)
