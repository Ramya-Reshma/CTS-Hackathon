import sqlite3
import json

conn = sqlite3.connect('uc10_anomalies.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=" * 80)
print("TABLES IN DATABASE:")
print("=" * 80)
for table in tables:
    print(f"\n📋 Table: {table[0]}")
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print(f"   Columns: {len(columns)}")
    for col in columns:
        print(f"     - {col[1]} ({col[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    row_count = cursor.fetchone()[0]
    print(f"   Rows: {row_count}")
    
    # Get sample data
    if row_count > 0:
        cursor.execute(f"SELECT * FROM {table[0]} LIMIT 3")
        sample_rows = cursor.fetchall()
        print(f"   Sample data (first 3 rows):")
        for row in sample_rows:
            print(f"     {row}")

print("\n" + "=" * 80)
conn.close()
