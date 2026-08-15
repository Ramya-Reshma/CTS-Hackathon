import json
import requests
import boto3
from typing import Any, Dict
from UC10_Anomaly_Monitor.config import settings
from UC10_Anomaly_Monitor.rca import prompts, schemas


class RCAAgent:
    def __init__(self):
        self.url = settings.LM_STUDIO_URL
        self.model = settings.LM_STUDIO_MODEL
        self.timeout = settings.TIMEOUT_SECONDS
        self.aws_region = settings.AWS_REGION

    def _call_lm_studio(self, messages: list) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
        }
        print(f"Calling LM Studio at {self.url}/chat/completions (timeout={self.timeout}s)")
        resp = requests.post(f"{self.url}/chat/completions", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # Expecting the assistant text at choices[0].message.content
        try:
            content = data["choices"][0]["message"]["content"]
            print(f"LM Studio returned response of length {len(content)}")
            return content
        except Exception:
            return json.dumps(data)

    def _call_bedrock_fallback(self, messages: list) -> str:
        client = boto3.client("bedrock-runtime", region_name=self.aws_region)
        # Use the Converse/Invoke API - adapt to common bedrock runtime signature
        body = json.dumps({"messages": messages}).encode("utf-8")
        resp = client.invoke_model(modelId=self.model, contentType="application/json", accept="application/json", body=body)
        # response body may be bytes-like
        raw = resp.get("body")
        if hasattr(raw, "read"):
            text = raw.read().decode("utf-8")
        else:
            text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        return text

    def run_rca(self, evidence_package: Dict[str, Any]) -> schemas.RCAOutput:
        system = {"role": "system", "content": prompts.SYSTEM_PROMPT}
        user = {"role": "user", "content": prompts.USER_PROMPT_TEMPLATE.format(evidence=json.dumps(evidence_package, indent=2))}
        messages = [system, user]

        try:
            text = self._call_lm_studio(messages)
        except Exception:
            print("LM Studio call failed, attempting Bedrock fallback...")
            try:
                text = self._call_bedrock_fallback(messages)
            except Exception as e:
                print(f"Bedrock fallback failed: {e}")
                raise

        # LLM should return JSON; attempt to parse
        try:
            parsed = json.loads(text)
        except Exception:
            # If the model returned text with surrounding formatting, try to extract JSON block
            import re
            m = re.search(r"\{.*\}", text, flags=re.S)
            if m:
                parsed = json.loads(m.group(0))
            else:
                raise ValueError("LLM did not return valid JSON")

        # Validate against schema; if validation fails, attempt to normalize common keys
        from pydantic import ValidationError

        # Debug: show parsed keys for normalization
        print("LLM parsed JSON keys:", list(parsed.keys()) if isinstance(parsed, dict) else type(parsed))

        # Normalize parsed output into the RCA schema shape
        try:
            rca = schemas.RCAOutput.parse_obj(parsed)
            return rca
        except ValidationError:
            # map common alternative keys to the schema
            norm = {}
            norm["incident_id"] = parsed.get("incident_id") or parsed.get("record_id") or parsed.get("Record_ID") or evidence_package.get("record_id")
            norm["record_type"] = parsed.get("record_type") or parsed.get("Record_Type") or (parsed.get("evidence") or {}).get("record_type") or (evidence_package.get("evidence") or {}).get("record_type")
            norm["severity"] = parsed.get("severity") or parsed.get("level") or "MEDIUM"
            norm["summary"] = parsed.get("summary") or parsed.get("summary_text") or parsed.get("explanation", "")

            # Normalize parsed output into the RCA schema shape
            # signals
            signals = parsed.get("anomaly_signals") or parsed.get("signals") or {}
            norm["anomaly_signals"] = signals if isinstance(signals, dict) else {}

            # evidence fields: accept list or dict and coerce to list of strings
            ev = parsed.get("evidence") or parsed.get("evidence_items") or parsed
            if isinstance(ev, dict):
                ev_list = [f"{k}: {v}" for k, v in ev.items()]
            elif isinstance(ev, list):
                ev_list = [json.dumps(x) if isinstance(x, (dict, list)) else str(x) for x in ev]
            else:
                ev_list = [str(ev)]
            norm["evidence"] = ev_list
            # observed_facts coercion to list of strings
            obs = parsed.get("observed_facts") or parsed.get("facts") or parsed.get("observations") or []
            if isinstance(obs, dict):
                obs_list = [f"{k}: {v}" for k, v in obs.items()]
            elif isinstance(obs, list):
                obs_list = [json.dumps(x) if isinstance(x, (dict, list)) else str(x) for x in obs]
            else:
                obs_list = [str(obs)]
            norm["observed_facts"] = obs_list
            norm["possible_causes"] = parsed.get("possible_causes") or parsed.get("hypotheses") or []
            norm["likely_root_cause"] = parsed.get("likely_root_cause") or parsed.get("root_cause") or "Insufficient evidence to determine root cause."
            try:
                norm["confidence"] = float(parsed.get("confidence", 0.5))
            except Exception:
                norm["confidence"] = 0.5

            norm["impact"] = parsed.get("impact") or parsed.get("business_impact") or ""
            norm["recommended_actions"] = parsed.get("recommended_actions") or parsed.get("recommendations") or []
            norm["additional_checks_required"] = parsed.get("additional_checks_required") or parsed.get("next_checks") or []

            # final validation/coercion
            print("Normalized RCA dict keys:", list(norm.keys()))
            print("Normalized RCA dict preview:", {k: norm[k] for k in norm if k in ['incident_id','record_type','severity']})
            rca = schemas.RCAOutput.parse_obj(norm)
            return rca
