import json
import requests
import boto3
from typing import Any, Dict, List
from UC10_Anomaly_Monitor.config import settings
from UC10_Anomaly_Monitor.rca import prompts, schemas, rag


class RCAAgent:
    def __init__(self):
        self.use_bedrock = settings.USE_BEDROCK
        self.bedrock_model_id = settings.BEDROCK_MODEL_ID
        self.url = settings.LM_STUDIO_URL
        self.lm_studio_model = settings.LM_STUDIO_MODEL
        self.timeout = settings.TIMEOUT_SECONDS
        self.aws_region = settings.AWS_REGION
        
        print(f"RCAAgent initialized: using_bedrock={self.use_bedrock}, model={self.bedrock_model_id if self.use_bedrock else self.lm_studio_model}")

    def _call_lm_studio(self, messages: list) -> str:
        payload = {
            "model": self.lm_studio_model,
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

    def _call_bedrock(self, messages: list, system_prompt: str = None) -> str:
        """Call AWS Bedrock using the Converse API"""
        client = boto3.client("bedrock-runtime", region_name=self.aws_region)
        print(f"Calling AWS Bedrock model: {self.bedrock_model_id} (region={self.aws_region})")
        
        # Convert OpenAI format messages to Bedrock Converse API format
        # Bedrock expects content as a list of content blocks, NOT with "type" key
        bedrock_messages = []
        for msg in messages:
            bedrock_msg = {
                "role": msg["role"],
                "content": [{"text": msg["content"]}]  # No "type" key - just text
            }
            bedrock_messages.append(bedrock_msg)
        
        try:
            # Build kwargs for converse API
            converse_kwargs = {
                "modelId": self.bedrock_model_id,
                "messages": bedrock_messages,
                "inferenceConfig": {
                    "maxTokens": 4096,
                    "temperature": 0.7,
                    "topP": 0.9,
                }
            }
            
            # Add system prompt if provided (Bedrock uses separate 'system' parameter)
            # System should be a list with text blocks, no "type" key
            if system_prompt:
                converse_kwargs["system"] = [{"text": system_prompt}]
            
            # Use Converse API (recommended for chat models)
            response = client.converse(**converse_kwargs)
            
            # Extract content from response
            if response.get("output") and response["output"].get("message"):
                content_blocks = response["output"]["message"].get("content", [])
                if content_blocks and "text" in content_blocks[0]:
                    text = content_blocks[0]["text"]
                    print(f"Bedrock returned response of length {len(text)}")
                    return text
            
            raise ValueError(f"Unexpected Bedrock response format: {response}")
        except Exception as e:
            print(f"Bedrock Converse API error: {e}")
            raise

    def run_rca(self, evidence_package: Dict[str, Any]) -> schemas.RCAOutput:
        system_prompt = prompts.SYSTEM_PROMPT
        user_content = prompts.USER_PROMPT_TEMPLATE.format(evidence=json.dumps(evidence_package, indent=2))
        user_message = {"role": "user", "content": user_content}
        messages = [user_message]

        text = None
        if self.use_bedrock:
            try:
                text = self._call_bedrock(messages, system_prompt=system_prompt)
            except Exception as e:
                print(f"Bedrock call failed ({e}), attempting LM Studio fallback...")
                try:
                    # LM Studio needs system in messages
                    full_messages = [{"role": "system", "content": system_prompt}, user_message]
                    text = self._call_lm_studio(full_messages)
                except Exception as e2:
                    print(f"LM Studio fallback also failed: {e2}")
                    raise
        else:
            try:
                # LM Studio needs system in messages
                full_messages = [{"role": "system", "content": system_prompt}, user_message]
                text = self._call_lm_studio(full_messages)
            except Exception as e:
                print(f"LM Studio call failed ({e}), attempting Bedrock fallback...")
                try:
                    text = self._call_bedrock(messages, system_prompt=system_prompt)
                except Exception as e2:
                    print(f"Bedrock fallback also failed: {e2}")
                    raise

        return self._parse_and_validate(text, evidence_package)

    def run_rag_rca(self, evidence_package: Dict[str, Any], historical_cases: List[Dict[str, Any]] | None = None, kb_path: str | None = None) -> schemas.RCAOutput:
        if historical_cases is None:
            historical_cases = rag.retrieve_similar_cases(evidence_package, kb_path=kb_path, limit=5)

        prompt = rag.build_rag_prompt(evidence_package, historical_cases)
        system_prompt = prompts.SYSTEM_PROMPT
        user_message = {"role": "user", "content": prompt}
        messages = [user_message]

        text = None
        if self.use_bedrock:
            try:
                text = self._call_bedrock(messages, system_prompt=system_prompt)
            except Exception as e:
                print(f"Bedrock RAG call failed ({e}), attempting LM Studio fallback...")
                try:
                    # LM Studio needs system in messages
                    full_messages = [{"role": "system", "content": system_prompt}, user_message]
                    text = self._call_lm_studio(full_messages)
                except Exception as e2:
                    print(f"LM Studio fallback also failed: {e2}")
                    raise
        else:
            try:
                # LM Studio needs system in messages
                full_messages = [{"role": "system", "content": system_prompt}, user_message]
                text = self._call_lm_studio(full_messages)
            except Exception as e:
                print(f"LM Studio RAG call failed ({e}), attempting Bedrock fallback...")
                try:
                    text = self._call_bedrock(messages, system_prompt=system_prompt)
                except Exception as e2:
                    print(f"Bedrock fallback also failed: {e2}")
                    raise

        return self._parse_and_validate(text, evidence_package)

    def _parse_and_validate(self, text: str, evidence_package: Dict[str, Any]) -> schemas.RCAOutput:
        try:
            parsed = json.loads(text)
        except Exception:
            import re
            m = re.search(r"\{.*\}", text, flags=re.S)
            if m:
                parsed = json.loads(m.group(0))
            else:
                raise ValueError("LLM did not return valid JSON")

        from pydantic import ValidationError

        # Ensure parsed is a dict
        if not isinstance(parsed, dict):
            print(f"WARNING: LLM returned non-dict type: {type(parsed)}, attempting to wrap...")
            parsed = {"incident_id": evidence_package.get("record_id"), "evidence": parsed}

        print("LLM parsed JSON keys:", list(parsed.keys()) if isinstance(parsed, dict) else type(parsed))

        try:
            return schemas.RCAOutput.parse_obj(parsed)
        except ValidationError:
            norm = {}
            try:
                norm["incident_id"] = parsed.get("incident_id") or parsed.get("record_id") or parsed.get("Record_ID") or evidence_package.get("record_id")
                
                # Safely extract record_type - evidence might be a list
                record_type = parsed.get("record_type") or parsed.get("Record_Type")
                if not record_type:
                    evidence_obj = parsed.get("evidence")
                    if isinstance(evidence_obj, dict):
                        record_type = evidence_obj.get("record_type")
                if not record_type:
                    evidence_obj = evidence_package.get("evidence")
                    if isinstance(evidence_obj, dict):
                        record_type = evidence_obj.get("record_type")
                norm["record_type"] = record_type or "CLAIM"
                
                norm["severity"] = parsed.get("severity") or parsed.get("level") or "MEDIUM"
                
                summary = parsed.get("summary") or parsed.get("summary_text") or parsed.get("explanation") or ""
                norm["summary"] = summary if isinstance(summary, str) else str(summary)

                signals = parsed.get("anomaly_signals") or parsed.get("signals") or {}
                norm["anomaly_signals"] = signals if isinstance(signals, dict) else {}

                # Safely extract and convert evidence
                ev = parsed.get("evidence") or parsed.get("evidence_items")
                if not ev:
                    ev_list = []
                elif isinstance(ev, dict):
                    ev_list = [f"{k}: {v}" for k, v in ev.items()]
                elif isinstance(ev, list):
                    ev_list = [json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x) for x in ev]
                else:
                    ev_list = [str(ev)]
                norm["evidence"] = ev_list

                # Safely extract and convert observed_facts
                obs = parsed.get("observed_facts") or parsed.get("facts") or parsed.get("observations")
                if not obs:
                    obs_list = []
                elif isinstance(obs, dict):
                    obs_list = [f"{k}: {v}" for k, v in obs.items()]
                elif isinstance(obs, list):
                    obs_list = [json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x) for x in obs]
                else:
                    obs_list = [str(obs)]
                norm["observed_facts"] = obs_list

                # Extract and ensure list types
                possible_causes = parsed.get("possible_causes") or parsed.get("hypotheses") or []
                norm["possible_causes"] = possible_causes if isinstance(possible_causes, list) else [str(possible_causes)]
                
                likely_root_cause = parsed.get("likely_root_cause") or parsed.get("root_cause") or "Insufficient evidence to determine root cause."
                norm["likely_root_cause"] = likely_root_cause if isinstance(likely_root_cause, str) else str(likely_root_cause)
                
                try:
                    norm["confidence"] = float(parsed.get("confidence") or parsed.get("confidence_level") or 0.5)
                except (ValueError, TypeError):
                    norm["confidence"] = 0.5

                impact = parsed.get("impact") or parsed.get("business_impact") or ""
                norm["impact"] = impact if isinstance(impact, str) else str(impact)
                
                recommended_actions = parsed.get("recommended_actions") or parsed.get("recommendations") or []
                norm["recommended_actions"] = recommended_actions if isinstance(recommended_actions, list) else [str(recommended_actions)]
                
                additional_checks = parsed.get("additional_checks_required") or parsed.get("additional_checks") or parsed.get("next_checks") or []
                norm["additional_checks_required"] = additional_checks if isinstance(additional_checks, list) else [str(additional_checks)]

                print("Normalized RCA dict keys:", list(norm.keys()))
                print("Normalized RCA dict preview:", {k: norm[k] for k in norm if k in ['incident_id','record_type','severity']})
            except Exception as norm_err:
                print(f"ERROR during normalization: {norm_err}")
                raise ValueError(f"Failed to normalize LLM output: {norm_err}")
            
            return schemas.RCAOutput.parse_obj(norm)
