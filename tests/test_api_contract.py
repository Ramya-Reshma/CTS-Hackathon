import requests

BASE_URL = "http://localhost:8000/api"


def _get_latest_run_id():
    response = requests.get(f"{BASE_URL}/runs", timeout=15)
    response.raise_for_status()
    payload = response.json()
    records = payload.get("records", [])
    assert records, "No runs found to validate"
    return records[0]["id"]


def test_anomalies_endpoint_contract_latest_run():
    run_id = _get_latest_run_id()

    response = requests.get(f"{BASE_URL}/runs/{run_id}/anomalies", timeout=20)
    response.raise_for_status()
    payload = response.json()

    records = payload.get("records", [])
    total = payload.get("total")

    assert isinstance(records, list)
    assert total == len(records) or total >= len(records)

    for record in records:
        record_id = str(record.get("record_id", ""))
        record_type = str(record.get("record_type", ""))

        assert record_id, "record_id must be present"
        assert not record_id.upper().startswith("UNKNOWN"), f"invalid record_id: {record_id}"
        assert record_type and record_type.upper() != "UNKNOWN", f"invalid record_type: {record_type}"


def test_anomaly_detail_has_rca_capable_fields():
    run_id = _get_latest_run_id()

    response = requests.get(f"{BASE_URL}/runs/{run_id}/anomalies", timeout=20)
    response.raise_for_status()
    records = response.json().get("records", [])

    assert records, "No anomalies found in latest run"
    anomaly_id = records[0]["id"]

    detail_response = requests.get(f"{BASE_URL}/anomalies/{anomaly_id}", timeout=20)
    detail_response.raise_for_status()
    detail = detail_response.json()

    expected_keys = [
        "record_id",
        "record_type",
        "severity",
        "likely_root_cause",
        "recommended_action",
        "evidence",
        "observed_facts",
        "possible_causes",
        "impact",
        "additional_checks",
        "anomaly_signals",
    ]

    for key in expected_keys:
        assert key in detail, f"Missing key in detail response: {key}"
