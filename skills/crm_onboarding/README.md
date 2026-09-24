# CRM Onboarding Skill

A deterministic, standard-library-only workflow for importing caller batches into
a local SQLite CRM and queuing rendered welcome messages. It makes no network
calls.

## Input columns

CSV must have exactly these headers: `phone`, `name`, `service`, `source`.
JSON must be an array of objects with the same fields. International numbers may
use a leading `+`; domestic numbers are stored without punctuation or a leading
zero. No country code is guessed.

## Run

```powershell
.\skills\crm_onboarding\run-client-workflow.ps1 `
  -LeadFile 'C:\path\to\leads.csv' `
  -TemplateId 'welcome_v1'
```

The runner passes a JSON request over stdin, creates
`data\local_crm.db`, and writes the result atomically to `logs\last_run.json`.
A concise execution record is appended to `logs\crm_onboarding_audit.jsonl`.
No message is transmitted by this skill; it only writes to the local dispatch
queue table.

## Test

```powershell
python -m unittest discover -s skills\crm_onboarding -p 'test_*.py' -v
```
