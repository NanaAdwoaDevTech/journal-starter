# Phase 6 evidence

Text output from the live run, captured while the stack was up. Nothing here
contains a secret value.

## Already proven (Nov 22)

- CloudTrail trail `journal-audit-trail` logging, multi-region, log validation on, 100-day retention.
- Test security group create, authorize and delete found in the S3 log files.
- Three alert emails received from the EventBridge and SNS rule.

## Proven in the live run

| Step | Command | Result |
|---|---|---|
| 1. Service identity | `aws eks list-pod-identity-associations` | [pending] |
| 2. Secrets from the vault | `kubectl -n journal exec deploy/journal-api -- printenv` (names only) | [pending] |
| 3. Private database | `aws rds describe-db-instances` and the connection tests | [pending] |
| 4. HTTPS and HSTS | `curl -v`, `curl -sI http://...`, `curl -sI https://.../version` | [pending] |
| 7. CodeQL on the latest commit | Actions run for the commit that `/version` reports | [pending] |
