import json
import re
import requests
import boto3
from typing import Any, Dict, List, Optional
from UC10_Anomaly_Monitor.config import settings
from UC10_Anomaly_Monitor.rca import prompts, schemas, rag


class RCAAgent:
    """
    Root Cause Analysis Agent.
    Orchestrates evidence reasoning, RAG knowledge synthesis, and AWS Bedrock LLM generation.
    """

    def __init__(self):
        self.use_bedrock = settings.USE_BEDROCK
        self.bedrock_model_id = settings.BEDROCK_MODEL_ID
        self.aws_region = settings.AWS_REGION
        self.url = settings.LM_STUDIO_URL
        self.lm_studio_model = settings.LM_STUDIO_MODEL
        self.timeout = settings.TIMEOUT_SECONDS
        
        print(f"[RCAAgent] Initialized: use_bedrock={self.use_bedrock}, model={self.bedrock_model_id if self.use_bedrock else self.lm_studio_model}, region={self.aws_region}")

    def _call_bedrock(self, messages: list, system_prompt: Optional[str] = None) -> str:
        """Call AWS Bedrock using the Converse API with existing configuration."""
        client = boto3.client("bedrock-runtime", region_name=self.aws_region)
        print(f"[RCAAgent] Invoking AWS Bedrock model: {self.bedrock_model_id} (region={self.aws_region})")
        
        bedrock_messages = []
        for msg in messages:
            bedrock_messages.append({
                "role": msg["role"],
                "content": [{"text": msg["content"]}]
            })
        
        converse_kwargs = {
            "modelId": self.bedrock_model_id,
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "topP": 0.9,
            }
        }
        
        if system_prompt:
            converse_kwargs["system"] = [{"text": system_prompt}]
        
        response = client.converse(**converse_kwargs)
        
        if response.get("output") and response["output"].get("message"):
            content_blocks = response["output"]["message"].get("content", [])
            if content_blocks and "text" in content_blocks[0]:
                return content_blocks[0]["text"]
        
        raise ValueError(f"Unexpected Bedrock response structure: {response}")

    def _call_lm_studio(self, messages: list) -> str:
        """Fallback to local LM Studio when configured."""
        payload = {
            "model": self.lm_studio_model,
            "messages": messages,
            "temperature": 0.3
        }
        print(f"[RCAAgent] Calling LM Studio at {self.url}/chat/completions")
        resp = requests.post(f"{self.url}/chat/completions", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _generate_llm_response(self, user_content: str, system_prompt: str) -> str:
        """Execute LLM call using primary Bedrock with graceful fallback."""
        messages = [{"role": "user", "content": user_content}]

        if self.use_bedrock:
            try:
                return self._call_bedrock(messages, system_prompt=system_prompt)
            except Exception as e:
                print(f"[RCAAgent] Bedrock call failed: {e}. Trying LM Studio fallback...")
                try:
                    full_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                    return self._call_lm_studio(full_messages)
                except Exception as e2:
                    print(f"[RCAAgent] LM Studio fallback also failed: {e2}")
                    raise e
        else:
            try:
                full_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                return self._call_lm_studio(full_messages)
            except Exception as e:
                print(f"[RCAAgent] LM Studio failed: {e}. Trying Bedrock fallback...")
                return self._call_bedrock(messages, system_prompt=system_prompt)

    def run_rag_rca(
        self,
        evidence_package: Dict[str, Any],
        historical_cases: Optional[List[Dict[str, Any]]] = None,
        kb_path: Optional[str] = None
    ) -> schemas.RCAAnalysis:
        """
        Execute full RAG-grounded RCA for an anomalous record.
        """
        # Step 1: Retrieve top-5 RAG cases if not already provided
        if historical_cases is None:
            historical_cases = rag.retrieve_similar_cases(evidence_package, kb_path=kb_path, limit=5)

        # Step 2: Build prompt
        system_prompt = prompts.SYSTEM_PROMPT
        user_prompt = rag.build_rag_prompt(evidence_package, historical_cases)

        # Step 3: Call LLM
        try:
            raw_text = self._generate_llm_response(user_prompt, system_prompt)
            return self._parse_and_validate(raw_text, evidence_package, historical_cases)
        except Exception as e:
            print(f"[RCAAgent] LLM execution failed ({e}); generating deterministic RAG recommendation.")
            return rag.generate_rag_recommendation(evidence_package, kb_path=kb_path)

    def run_rca(self, evidence_package: Dict[str, Any]) -> schemas.RCAAnalysis:
        """Run RCA without explicit RAG retrieval (backwards compatibility)."""
        return self.run_rag_rca(evidence_package)

    def _parse_and_validate(
        self,
        text: str,
        evidence_package: Dict[str, Any],
        historical_cases: List[Dict[str, Any]]
    ) -> schemas.RCAAnalysis:
        """
        Parse raw LLM output, validate JSON schema, and normalize fields safely.
        """
        # Clean potential markdown formatting
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except Exception:
            m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
            else:
                raise ValueError("LLM response did not contain valid JSON object.")

        if not isinstance(parsed, dict):
            raise ValueError(f"LLM returned invalid non-dict root: {type(parsed)}")

        # Normalization and field extraction
        rec_id = str(parsed.get("record_id") or evidence_package.get("record_id") or "UNKNOWN")
        
        # Determine priority
        iso_sev = evidence_package.get("isolation_forest", {}).get("severity_0to1", 0.0)
        signal_count = evidence_package.get("ml_signal_count", 0)
        
        priority = parsed.get("priority") or ("HIGH" if (iso_sev and iso_sev >= 0.8) or signal_count >= 2 else "MEDIUM")
        priority = str(priority).upper().strip()
        if priority not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            priority = "MEDIUM"

        anomaly_type = str(parsed.get("anomaly_type") or evidence_package.get("anomaly_type") or f"{evidence_package.get('record_type', 'Claim')} Anomaly")
        root_cause = str(parsed.get("root_cause") or "Record was flagged by anomaly detection models.")
        
        # Ensure observed_facts is a list of strings
        obs = parsed.get("observed_facts")
        if isinstance(obs, list):
            observed_facts = [str(x) for x in obs if x]
        elif isinstance(obs, str):
            observed_facts = [obs]
        else:
            observed_facts = [f"Record {rec_id} was analyzed by anomaly detection."]

        # Ensure possible_causes is a list of strings
        poss = parsed.get("possible_causes")
        if isinstance(poss, list):
            possible_causes = [str(x) for x in poss if x]
        elif isinstance(poss, str):
            possible_causes = [poss]
        else:
            possible_causes = ["Data or billing discrepancy requires review."]

        likely_root_cause = str(parsed.get("likely_root_cause") or "Insufficient evidence to determine root cause.")
        
        # Ensure recommended_actions is a list of strings
        acts = parsed.get("recommended_actions")
        if isinstance(acts, list):
            recommended_actions = [str(x) for x in acts if x]
        elif isinstance(acts, str):
            recommended_actions = [acts]
        else:
            recommended_actions = ["Validate the claim record against source documentation."]

        # Validate with Pydantic schema
        result = schemas.RCAAnalysis(
            priority=priority,
            record_id=rec_id,
            anomaly_type=anomaly_type,
            root_cause=root_cause,
            observed_facts=observed_facts,
            possible_causes=possible_causes,
            likely_root_cause=likely_root_cause,
            recommended_actions=recommended_actions
        )

        return result
