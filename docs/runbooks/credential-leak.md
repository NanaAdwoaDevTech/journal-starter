# Runbook: leaked credentials

Owner: NanaAdwoaDevTech. Last reviewed: 2026-11-17.
Scope: Journal API (AWS account, EKS, RDS, OpenAI, GitHub, DuckDNS).

## When to use this

Use it whenever a secret may have been exposed: pushed to git, pasted into
a chat or ticket, shown in a screenshot, printed in a log, or reported by
an alert (GuardDuty, GitHub secret scanning, OpenAI usage spike).

Assume the worst. Treat the credential as compromised until proven
otherwise. Rotating is cheap. Investigating comes after containment.
Never paste the leaked value anywhere new while handling the incident.

## 1. Identify what leaked (5 minutes)

Write down the time found, who found it, and how. Then find the row below.

| Credential | Where it lives | What an attacker could do |
|---|---|---|
| AWS IAM user password or access key | IAM user MyAdminUser | Full control of the AWS account |
| GitHub Actions role | IAM role github-actions-journal (no stored key) | Only via a workflow in this repo, limited by its trust policy |
| OpenAI API key | Secrets Manager secret journal/openai | Spend money, read usage, abuse the model |
| Database password | Secrets Manager secret journal/database-url | Read or change journal entries (needs network access to RDS) |
| DuckDNS token | Password manager | Point the domain at an attacker's server |
| GitHub token or Codespace session | github.com | Push code, change workflows |

## 2. Contain (first 15 minutes)

Do this before investigating. Do not delete logs or evidence.

1. AWS access key: set it inactive. This project has no long-lived keys,
   so finding one is itself a finding.
   `aws iam update-access-key --user-name <user> --access-key-id <key-id> --status Inactive`
2. AWS console password or login session: change the password, then in
   IAM open the user or role and choose "Revoke active sessions".
3. OpenAI key: revoke it in the OpenAI dashboard under API keys.
4. DuckDNS token: regenerate it on duckdns.org.
5. GitHub token: revoke it under Settings, Developer settings. If a
   workflow was changed without you, disable Actions until reviewed.
6. If the API itself is being abused, scale the deployment to zero:
   `kubectl -n journal scale deployment --all --replicas=0`

## 3. Rotate

Create the new value first, then update where it is used, then restart.
Never type a secret on the command line. Use `read -rsp` so it stays out of
shell history and Terraform state.

1. OpenAI: create a new key, then update the journal/openai secret using
   the same hand-set method used at deploy time.
2. Database: set a new password, update the journal/database-url secret,
   and change the password on the RDS instance to match.
3. DuckDNS: store the new token in your password manager only.
4. AWS IAM: replace the user's password and MFA if the account was in scope.
5. Restart the workloads so they read the new values:
   `kubectl -n journal get deploy`, then
   `kubectl -n journal rollout restart deploy/<name>`
6. Confirm the app works: `curl -s https://nana-journal.duckdns.org/version`

## 4. Check for unauthorized access

Look at the whole window from the time the secret was first exposed until
the moment it was disabled. Save the output in a private place, not in git.

1. AWS activity by the exposed user or key:
   `aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue=<user> --max-results 50`
   `aws cloudtrail lookup-events --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=<key-id> --max-results 50`
   Look for actions you did not take: new IAM users or keys, changed
   security groups, new roles, secrets read, resources created in regions
   you do not use.
2. GuardDuty findings:
   `aws guardduty list-detectors`, then
   `aws guardduty list-findings --detector-id <id>`
3. IAM state: confirm no unexpected users, roles, access keys or policies.
   `aws iam generate-credential-report`, then
   `aws iam get-credential-report`
4. OpenAI: open the usage page and compare spend and request counts with
   normal use. A spike means the key was used.
5. GitHub: check the account security log at github.com/settings/security-log,
   the repository's recent commits and workflow runs, and the Security tab
   for secret scanning alerts. Look for workflow files you did not write.
6. Application: look for unusual entries or deletions in the journal data.
   `kubectl -n journal logs deploy/<name> --since=24h`
7. Billing: check Cost Explorer for services you did not start.

Record the result as one of: no misuse found, misuse suspected, misuse
confirmed. If misuse is confirmed, rotate every credential in section 1,
not only the one that leaked, and consider rebuilding from a clean state.

## 5. Remove the secret from where it leaked

1. If it was committed to git, rotating is mandatory. Removing the commit
   does not make the secret safe, because forks, clones and caches may
   already have it.
2. Then rewrite the history with git filter-repo and force-push, and ask
   GitHub to clear cached views if the repository is public.
3. If it was in a screenshot, a chat or a ticket, delete the message and
   the image, and note where copies may remain.
4. Add the file or pattern to .gitignore. Keep GitHub push protection on.

## 6. Notify stakeholders

Notify early, even before the investigation is finished. Keep it factual.

Who to tell for this project:
- The course mentor or reviewer, if their access or work is affected.
- AWS Support, if the account was used by someone else.
- OpenAI, if the key was used. Ask about disputing the charges.
- Anyone whose personal data is stored in the journal, if it was read.

Message template:

> Subject: Security incident, credential exposed
> What happened: <one sentence, no secret values>
> When: found <date and time>, exposed since <date and time>
> What was affected: <credential, system, data>
> What we did: disabled and rotated at <time>
> Current status: <contained / investigating>
> What we need from you: <nothing / action>
> Next update: <time>

Never include the leaked value, or any other secret, in the message.

## 7. Recover

1. Confirm the new credentials work and the old ones are rejected.
2. Confirm the app is healthy and `/version` returns the expected commit.
3. Turn workloads back on if they were scaled to zero.
4. Keep CloudTrail and GuardDuty alerts watched for the next 7 days.

## 8. Post-incident review (within a week)

Write a short timeline and answer these questions:

1. How did the secret leak, and why was it possible?
2. How long was it exposed, and how long until it was contained?
3. Was it used? What was the impact?
4. What control would have prevented it or caught it sooner?
5. What changes will we make, who owns each one, and by when?

Update this runbook with anything that was unclear or missing.
