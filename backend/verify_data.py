import sqlite3
import json

conn = sqlite3.connect('uc10_anomalies.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("VERIFYING DATA IN SQLITE DATABASE: uc10_anomalies.db")
print("=" * 80)

# Check table existence
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"\n✅ Tables found: {len(tables)}")
for table in tables:
    print(f"   - {table['name']}")

# Check anomaly_results table
print("\n" + "=" * 80)
print("ANOMALY_RESULTS TABLE")
print("=" * 80)

cursor.execute("SELECT COUNT(*) as count FROM anomaly_results")
total_records = cursor.fetchone()['count']
print(f"✅ Total Records: {total_records}")

# Check by severity
cursor.execute("""
    SELECT severity, COUNT(*) as count 
    FROM anomaly_results 
    GROUP BY severity
    ORDER BY count DESC
""")
print("\n📊 Records by Severity:")
for row in cursor.fetchall():
    print(f"   {row['severity']}: {row['count']}")

# Check by record type
cursor.execute("""
    SELECT record_type, COUNT(*) as count 
    FROM anomaly_results 
    GROUP BY record_type
    ORDER BY count DESC
""")
print("\n📋 Records by Type:")
for row in cursor.fetchall():
    print(f"   {row['record_type']}: {row['count']}")

# Show sample data with all columns
print("\n" + "=" * 80)
print("SAMPLE DATA (First 5 records)")
print("=" * 80)

cursor.execute("""
    SELECT * FROM anomaly_results 
    ORDER BY created_at DESC 
    LIMIT 5
""")

for idx, row in enumerate(cursor.fetchall(), 1):
    print(f"\n📌 Record #{idx}:")
    print(f"   ID: {row['id']}")
    print(f"   Run ID: {row['run_id']}")
    print(f"   Record ID: {row['record_id']}")
    print(f"   Type: {row['record_type']}")
    print(f"   Severity: {row['severity']}")
    print(f"   Confidence: {row['confidence']}")
    print(f"   Created: {row['created_at']}")
    if row['full_record']:
        data = json.loads(row['full_record'])
        print(f"   Full Record Keys: {list(data.keys())}")

print("\n" + "=" * 80)
print("✅ ALL DATA IS STORED IN SQLite DATABASE")
print("=" * 80)

conn.close()
