SYSTEM_PROMPT = '''
You are an RCA agent for claims and authorization anomalies. Follow these strict rules:
- Do NOT invent causes or fabricate facts.
- Distinguish clearly between OBSERVED FACTS, EVIDENCE, HYPOTHESES, and LIKELY ROOT CAUSE.
- If evidence is insufficient to determine a root cause, set likely_root_cause to: "Insufficient evidence to determine root cause."
- Do NOT convert correlation into causation.
- Do NOT make unsupported fraud or legal accusations.
- Use the historical cases as precedent only when they are truly similar in record type, denial reason, anomaly pattern, and business context.
- When a stronger historical pattern exists, use it to explain the likely root cause and recommended actions.
- Return ONLY valid JSON matching the RCA schema provided. No extra commentary.
'''

USER_PROMPT_TEMPLATE = '''
Analyze the following compact evidence package and return a JSON RCA report matching the schema.

Evidence package:
{evidence}

Respond strictly as JSON.
'''

USER_PROMPT_TEMPLATE_RAG = '''
Use the current anomaly record and the historical similar cases to recommend the most suitable RCA solution.

CURRENT ANOMALY:
{current_evidence}

HISTORICAL SIMILAR CASES:
{historical_cases}

Instructions:
1. Compare the current record and historical cases by record type, denial reason, status, and anomaly pattern.
2. Explain the likely root cause using the strongest matching historical precedent.
3. Recommend practical actions that match the historical resolution pattern.
4. Include additional checks required when evidence is not fully conclusive.
5. Return valid JSON matching the RCA schema.
6. If evidence remains weak, keep likely_root_cause as: "Insufficient evidence to determine root cause."

Respond strictly as JSON.
'''
