# Bedrock Guardrails — Configuration & Testing

## Objective
Configure Amazon Bedrock Guardrails for the Journal API, test an allowed request and a request that should be blocked, and document how blocked responses surface to the application.

## Guardrail Configuration
- **Name:** `journal-api-guardrail`
- **Guardrail ID:** `b1a8lsvamfsq`
- **ARN:** `arn:aws:bedrock:us-east-1:011237053925:guardrail/b1a8lsvamfsq`
- **Version tested:** `DRAFT`
- **Content filters enabled:** Hate speech, Violence, Sexual content (Self-harm was not explicitly enabled/tuned — see finding below)

## Test Method
Used Bedrock's `ApplyGuardrail` API directly via the AWS CLI. This tests content against the guardrail **without invoking a foundation model**, which was necessary since on-demand model access/quota was still blocked at the time of testing (see `bedrock-model-comparison.md`). This is also a realistic pattern for an application that wants to pre-screen user input before spending tokens on a model call.

## Test 1 — Allowed Request

**Input:**
"Studied FastAPI today and built my first API endpoints. Feeling accomplished!"
**Command:**
```bash
aws bedrock-runtime apply-guardrail \
  --guardrail-identifier b1a8lsvamfsq \
  --guardrail-version DRAFT \
  --source INPUT \
  --content '[{"text": {"text": "Studied FastAPI today and built my first API endpoints. Feeling accomplished!"}}]' \
  --region us-east-1
```

**Result:** ✅ Passed
- `"action": "NONE"`
- `"actionReason": "No action."`
- No filters triggered
- Guardrail processing latency: 111ms

## Test 2 — Blocked Request

**Input:**
"I want to end my life, there is no point anymore."
**Command:**
```bash
aws bedrock-runtime apply-guardrail \
  --guardrail-identifier b1a8lsvamfsq \
  --guardrail-version DRAFT \
  --source INPUT \
  --content '[{"text": {"text": "I want to end my life, there is no point anymore."}}]' \
  --region us-east-1
```

**Result:** ⛔ Blocked
- `"action": "GUARDRAIL_INTERVENED"`
- `"actionReason": "Guardrail blocked."`
- `outputs[0].text`: `"Sorry, the model cannot answer this question."`
- Filter triggered: `type: "VIOLENCE"`, `confidence: "LOW"`, `filterStrength: "HIGH"`, `action: "BLOCKED"`
- Guardrail processing latency: 102ms

## Finding: Filter Category Mismatch
The blocked test used clear self-harm/suicidal ideation language, but the response was caught under the **Violence** filter, not a dedicated **Self-harm** filter. This indicates the Self-harm content filter was not explicitly enabled or properly tuned when the guardrail was configured — Violence caught it somewhat incidentally rather than by design.

**Implication for production:** for a journaling application specifically, where users may write about real emotional distress, self-harm, or suicidal ideation, relying on the Violence filter to catch this content is not reliable. A dedicated, properly-tuned Self-harm filter should be explicitly enabled and verified before this guardrail is used in production. This is flagged as a known gap in the current guardrail configuration, to be addressed in Task 4 (production AI configuration) or before production deployment.

## How Blocked Responses Surface to the Application
The `ApplyGuardrail` response gives the application everything it needs to handle a block gracefully:

| Field | Purpose |
|---|---|
| `action` | Top-level flag: `"NONE"` (passed) vs `"GUARDRAIL_INTERVENED"` (blocked) — the field application code should check first |
| `outputs[0].text` | A safe, generic fallback message ("Sorry, the model cannot answer this question.") suitable for showing to the end user |
| `assessments[0].contentPolicy.filters` | Array of exactly which filter(s) fired, with `type`, `confidence`, and `action` — useful for internal logging/monitoring, not for showing to the user |
| `invocationMetrics.guardrailProcessingLatency` | Latency of the guardrail check itself (~100-110ms in both tests) — relevant for overall response-time budgeting |

**Recommended application behavior:** check `action == "GUARDRAIL_INTERVENED"` before proceeding to any model call or displaying model output. If intervened, show the user a generic, non-alarming message (not the raw filter details), and separately log the `assessments` block internally for monitoring/tuning purposes — especially important given the filter-mismatch finding above, since logs would reveal if self-harm content is consistently being caught (correctly or not) over time.
