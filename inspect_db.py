import sqlite3
import json
import os

conn = sqlite3.connect('backend/uc10_anomalies.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get a HIGH severity record
cur.execute("""SELECT full_record, anomaly_signals, anomaly_type, primary_signal,
               severity, record_id, likely_root_cause, recommended_action, confidence
               FROM anomaly_results WHERE severity='HIGH' LIMIT 1""")
row = cur.fetchone()
if row:
    fr = json.loads(row['full_record']) if row['full_record'] else {}
    sig = json.loads(row['anomaly_signals']) if row['anomaly_signals'] else {}
    print('record_id:', row['record_id'])
    print('severity:', row['severity'])
    print('anomaly_type:', row['anomaly_type'])
    print('primary_signal:', row['primary_signal'])
    print('confidence:', row['confidence'])
    print('likely_root_cause:', (row['likely_root_cause'] or '')[:120])
    print()
    print('=== FULL RECORD KEYS ===')
    for k in sorted(fr.keys()):
        print(f'  {k}: {repr(fr[k])[:80]}')
    print()
    print('=== ANOMALY SIGNALS ===')
    print(json.dumps(sig, indent=2)[:2000])

# Quality report
qpath = 'log/quality_report.json'
if os.path.exists(qpath):
    with open(qpath, encoding='utf-8') as f:
        q = json.load(f)
    print()
    print('=== QUALITY REPORT KEYS ===')
    if isinstance(q, dict):
        for k, v in q.items():
            print(f'  {k}: {repr(v)[:120]}')

# SLA temporal findings
spath = 'log/sla_temporal_findings.json'
if os.path.exists(spath):
    with open(spath, encoding='utf-8') as f:
        s = json.load(f)
    print()
    print('=== SLA FINDINGS ===')
    if isinstance(s, dict):
        for k, v in s.items():
            print(f'  {k}: {repr(v)[:120]}')
    elif isinstance(s, list) and len(s) > 0:
        print(f'LIST of {len(s)} records; first:')
        for k, v in s[0].items():
            print(f'  {k}: {repr(v)[:80]}')

conn.close()
