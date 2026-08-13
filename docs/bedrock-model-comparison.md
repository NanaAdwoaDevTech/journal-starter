# Bedrock Model Comparison — Journal API Sentiment Analysis

## Objective
Compare foundation models on Amazon Bedrock against the Journal API's sentiment-analysis workload, evaluating response quality, latency, cost, quota limits, and structured-response support.

## Test Setup
- **Prompt source:** Journal API's actual system + user prompt (`api/services/llm_service.py`)
- **System prompt:** instructs the model to return ONLY a JSON object with keys `sentiment` (positive/negative/neutral), `summary` (2 sentences), and `topics` (2–4 short strings)
- **Test entry:** a sample journal entry about learning FastAPI and struggling with async/await
- **Method:** Amazon Bedrock Converse API (`aws bedrock-runtime converse`), called via AWS CLI, timed with `time`
- **Region:** us-east-1

## Models Tested

| Model | Model ID | Provider |
|---|---|---|
| Claude Sonnet 5 | `anthropic.claude-sonnet-5` | Anthropic |
| DeepSeek V3.2 | `deepseek.v3.2` | DeepSeek |
| Nova Lite | `amazon.nova-lite-v1:0` | Amazon |

## Results

### Claude Sonnet 5
- **Status:** ❌ Blocked — `AccessDeniedException`
- **Finding:** Anthropic models on Bedrock require a one-time use-case access request (company name, URL, reason for access) before first use, separate from the general model catalog. This is a documented Anthropic-specific gate, not a bug — confirmed via the Bedrock console's own Model Access page, which states Anthropic models require submitting use-case details before first-time use.
- **Access request submitted:** [date] — pending approval at time of writing.

### DeepSeek V3.2
- **Status:** ❌ Blocked — `ThrottlingException` ("Too many tokens per day")
- **Finding:** Investigated via `aws service-quotas list-service-quotas`. Every relevant quota for DeepSeek V3.2 — on-demand requests/minute, on-demand tokens/minute, and max tokens/day — is set to **0.0** by default on this account. This is not a rate-limit in the traditional sense; it's a zero-provisioned quota requiring an explicit increase request before any on-demand inference is possible.

### Nova Lite
- **Status:** ❌ Blocked — `ThrottlingException` ("Too many tokens per day")
- **Finding:** Same root cause as DeepSeek. Checked via the same `list-service-quotas` command — every Nova Lite on-demand quota also shows **0.0**. This confirms the restriction is **account-wide**, not model-specific: this AWS account currently has no on-demand Bedrock inference quota provisioned for *any* model tested.

## Root Cause & Resolution Path
New AWS accounts can start with Bedrock on-demand quotas locked at `0`, pending backend account verification. The self-service "Request increase at account level" button in the Service Quotas console was found to be **disabled/grayed out** for these quotas — meaning even the standard self-service quota-increase path is unavailable at this stage.

**Resolution in progress:** opened an AWS Support case (Service limit increase → Bedrock) requesting on-demand inference quota provisioning, since self-service channels were unavailable. Case ID 178665864500161, opened [add date], unresolved as of this commit.

## What This Confirms (per the task's requirements)
- **Quota limits:** ✅ Directly observed and documented — every tested model shows 0.0 on-demand quota by default on a new account, and the standard self-service increase path was itself blocked, requiring an AWS Support case.
- **Response quality / latency / cost / structured-response support:** ⏳ Pending — cannot be evaluated until at least one model successfully returns a response. Will update this document once the Support case resolves and/or Anthropic access is approved.

## Next Steps
1. Await AWS Support resolution on the quota increase request.
2. Await Anthropic use-case approval for Claude Sonnet 5.
3. Once at least 2 models are reachable, re-run the identical `messages.json` / `system.json` prompt against each and record:
   - Whether the JSON response is valid and matches the required schema (`sentiment`, `summary`, `topics`)
   - Wall-clock latency (`time` command output)
   - Input/output token counts (from the Converse API's `usage` field in the response)
   - Approximate cost, calculated from token counts × Bedrock's published per-model pricing
