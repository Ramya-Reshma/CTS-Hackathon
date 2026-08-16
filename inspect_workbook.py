import pandas as pd
path = r'c:\Users\Admin\Desktop\Cognizant hackathon\Cts\CTS-Hackathon\healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx'
xl = pd.ExcelFile(path)
print('SHEETS:', xl.sheet_names)
for s in xl.sheet_names:
    df = pd.read_excel(path, sheet_name=s)
    print('--- SHEET:', s, 'ROWS=', len(df), 'COLS=', list(df.columns[:20]))
    print(df.head(3).to_string(index=False))
