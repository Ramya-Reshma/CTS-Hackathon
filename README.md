UC10 – Claims and Authorization Data-Quality Anomaly Monitor (RCA Agent)

Run the ML pipeline (which writes `log/final_anomaly_report.json`) and then run the RCA agent:

1. Run ML pipeline (example):

```bash
python ML/main.py Data/sample_input.csv
```

2. Run RCA agent for a specific record:

```bash
python -m UC10_Anomaly_Monitor.main PH201432
```

Configure LM Studio and model in `.env` or environment variables.
# CTS-Hackathon