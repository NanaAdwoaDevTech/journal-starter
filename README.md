# Learn to Cloud Phase 3 Capstone: Journal API

[![CI](https://github.com/NanaAdwoaDevTech/journal-starter/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/NanaAdwoaDevTech/journal-starter/actions/workflows/ci.yml)

Welcome to [Learn to Cloud's](https://learntocloud.com) Phase 3 capstone. You will be guided to building a journal API with **FastAPI**, **PostgreSQL**, structured logging, input validation, and AI-powered entry analysis.

## Capstone

These chapters will guide you and are meant to be completed in order. Each chapter builds on the previous one, so do not skip ahead. 

1. [Check the prerequisites](docs/01-prerequisites.md)
2. [Set up the project](docs/02-project-setup.md)
3. [Run the API](docs/03-run-the-api.md)
4. [Build GET for one entry](docs/04-get-entry.md)
5. [Build DELETE for one entry](docs/05-delete-entry.md)
6. [Add input validation and debug a partial update](docs/06-input-validation.md)
7. [Use logs to understand the API](docs/07-logging.md)
8. [Set up an AI provider](docs/08-ai-setup.md)
9. [Build AI-powered analysis](docs/09-ai-analysis.md)
10. [Finish the capstone](docs/10-finish.md)

**[Start the capstone →](docs/01-prerequisites.md)**

## Reference

This is additional reference material for the capstone in case you want to explore further or need help:

- [Testing and CI](docs/reference/testing-and-ci.md)
- [Troubleshooting](docs/reference/troubleshooting.md)
- [Sync your fork with upstream](docs/reference/upstream-sync.md)
- [Explore your database](docs/reference/explore-database.md)

> **Learning environment only:** This application has no authentication or
> per-user data isolation. Do not expose it publicly or store personal or
> sensitive journal content in it.
 
=================================================================

## My Section

**Deployment (Phase 4)**

Public base URL: https://nana-journal.duckdns.org 
Verifier result: passed Oct 26, 2026 (entry creation and live AI analysis). Test data only. The API has no user authentication or data isolation.

- **Public path:** internet -> Elastic IP -> Caddy (TLS) -> API container on `127.0.0.1:8000`.
- **Private path:** API -> PostgreSQL over the VPC. The database has no public address.
- **Administrative path:** IAM login -> Session Manager -> EC2. No SSH port and no key pair.
### Services selected
 
| Layer | Service | Why |
|---|---|---|
| Network | VPC, 2 public + 2 private subnets, internet gateway, **no NAT gateway** | Private tier for the database without the NAT hourly cost |
| App tier | EC2 `t3.micro`, Docker, Caddy, Elastic IP | Cheapest setup that gives public HTTPS and a stable address |
| HTTPS | Caddy + Let's Encrypt, DuckDNS hostname | Free, trusted, auto-renewing certificate |
| Database | RDS PostgreSQL (`db.t4g.micro`, single-AZ, 20 GiB gp3) | Managed, persistent, private |
| Admin access | AWS Systems Manager Session Manager | Authenticated access with no open management port |
| Secrets | SSM Parameter Store (SecureString) | Keeps credentials out of git, images, and logs |
| Cost control | AWS Budgets (`journal-api-deploy`, $40/month) | Alerts configured before provisioning |
 
### Expected cost
 
| Item | Estimate / month |
|---|---|
| EC2 `t3.micro` + 20 GiB gp3 | about $8 to $10 |
| RDS `db.t4g.micro` + 20 GiB gp3 | about $13 to $16 |
| Public IPv4 (Elastic IP) | about $3.60 |
| Session Manager, Parameter Store (standard) | $0 |
| Data transfer + OpenAI testing | under $2 |
| **Total** | **about $25 to $30 (about $1/day)** |
 
Estimates are approximate. Actual spend after deployment: **[fill in from Billing]**.
Estimate and budget created **before** provisioning (screenshots below).
 
### Access controls
 
- `journal-app-sg`: inbound **80 and 443 only**. No port 22.
- `journal-db-sg`: inbound **5432 only, from `journal-app-sg`** (not an IP range).
- RDS: **Publicly accessible = No**, DB subnet group contains only private subnets.
- EC2 role `journal-ec2-role`: Session Manager plus an inline policy that reads **only** `/journal/*` parameters.
- Secrets live in Parameter Store. They are loaded into environment variables at container start. They are not in the repo (`.env` is git-ignored and in `.dockerignore`), not in the image, and not in logs.
### AI model and safety controls
 
- **Model:** `gpt-6-luna` via the OpenAI Responses API. **[confirm model name]**
- Structured output with a strict JSON schema (sentiment, summary, topics only).
- Prompt tells the model to treat journal text as data, not instructions (prompt-injection defence).
- Server rejects unfinished, refused, blank, or non-object responses, then validates with Pydantic. The AI cannot set the entry ID or timestamp.
- 60-second timeout and one retry. Errors return generic messages with no journal text.
- Logs never contain journal text, provider responses, or credentials.
- Provider spending limit: **[fill in if configured]**
### Evidence that each constraint passed
 
| # | Constraint | How it is met | Evidence |
|---|---|---|---|
| 1 | Public HTTPS, trusted certificate | Caddy + Let's Encrypt on `nana-journal.duckdns.org` | `docs/img/padlock.png`, `docs/img/certificate.png` (issuer Let's Encrypt) |
| 2 | Private database | Private subnets, not public, SG allows only the app SG | `docs/img/rds-connectivity.png`, `docs/img/sg-inbound.png`, `docs/img/db-blocked-from-internet.png` (`BLOCKED`, resolves to `10.0.x.x`) |
| 3 | Private management, authenticated, no leaked credentials | Session Manager, no port 22, Parameter Store | `docs/img/session-manager.png`, `docs/img/app-sg.png`, `docs/img/parameter-store.png` |
| 4 | Survives logout and restart, data persists | Docker `--restart unless-stopped`, data in RDS | `docs/img/restart-test.png` (entry present after `docker restart`) |
| 5 | CRUD and live AI analysis | Same API code; secrets injected at runtime | `docs/img/db-tables.png`, `docs/img/verifier-passed.png` |
| 6 | Cost estimate and budget alerts before provisioning | Pricing Calculator estimate, AWS Budget | `docs/img/estimate.png`, `docs/img/budget.png` |
 
### Limitation to fix before production
 
**The public API has no authentication or rate limiting.** Anyone with the URL can create, read, and delete entries, and every `/analyze` call triggers a paid request to the AI provider. A bot could fill the database or run up the AI bill. Before real use I would add authentication, per-client rate limits, a provider spending cap with alerts, per-user data isolation, and disable the public `/docs` page.
 
### Cleanup
 
Resources kept for Phase 5: 
<img width="1568" height="687" alt="image" src="https://github.com/user-attachments/assets/389b3e0f-2d08-4937-a21a-5a460ef609e8" />
<img width="1568" height="715" alt="image" src="https://github.com/user-attachments/assets/f0504322-0d36-4381-b53c-2a0842cdf2cc" />
<img width="1568" height="717" alt="image" src="https://github.com/user-attachments/assets/f11f8cbf-c561-4ea1-9aa9-a406e9cc8c10" />
<img width="1568" height="653" alt="image" src="https://github.com/user-attachments/assets/db5180f3-bb29-4185-b763-454265d5363d" />
<img width="1568" height="715" alt="image" src="https://github.com/user-attachments/assets/664cb299-4bf7-4ef2-95ee-892964a631e7" />
<img width="1568" height="706" alt="image" src="https://github.com/user-attachments/assets/6337f565-05d5-414b-aaac-849285e18abd" />
<img width="1568" height="718" alt="image" src="https://github.com/user-attachments/assets/3ab6e3ae-6774-4cf1-83d6-4d879f60ce9c" />
<img width="1568" height="672" alt="image" src="https://github.com/user-attachments/assets/843749dd-7a0a-4802-9d2d-7b44c225fa6e" />
<img width="1568" height="664" alt="image" src="https://github.com/user-attachments/assets/4f2b60d6-98de-4ece-8ee7-a1a713420ea9" />
<img width="1568" height="663" alt="image" src="https://github.com/user-attachments/assets/285037f9-fba4-4066-96a1-1b6f9fa27fcb" />
<img width="1568" height="714" alt="image" src="https://github.com/user-attachments/assets/1e1f8ea6-1ebd-45e3-b9ef-ac2bfd65a34b" />
<img width="1568" height="720" alt="image" src="https://github.com/user-attachments/assets/febf2420-c620-4426-bb79-9ed27264234b" />
<img width="1568" height="686" alt="image" src="https://github.com/user-attachments/assets/9b81cd21-3499-4ede-ad71-1c0674c34681" />

Billing dashboard checked on: **26/10/2027**
Unexpected charges: **None**

=================================================================

## License

MIT License - see [LICENSE](LICENSE).
