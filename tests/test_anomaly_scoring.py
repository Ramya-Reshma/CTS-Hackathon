import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import result_service
from services.pipeline_adapter import get_severity_from_record


def test_single_signal_anomaly_is_medium():
    record = {"ISO_Severity_0to1": 1.0, "ML_Anomaly_Signal_Count": 1}
    assert get_severity_from_record(record) == "MEDIUM"


def test_multi_signal_anomaly_is_high():
    record = {
        "ISO_Severity_0to1": 0.96,
        "ML_Anomaly_Signal_Count": 2,
        "Correlation_Anomaly": True,
    }
    assert get_severity_from_record(record) == "HIGH"


def test_confidence_uses_signal_count():
    assert result_service._calculate_confidence({"ML_Anomaly_Signal_Count": 1}) == 0.5
    assert result_service._calculate_confidence({"ML_Anomaly_Signal_Count": 2}) == 0.75
    assert result_service._calculate_confidence({"ML_Anomaly_Signal_Count": 3}) == 0.9
