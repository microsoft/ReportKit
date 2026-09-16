# Operational Snapshot Demo

This directory contains a non-sensitive synthetic 401-record canonical sample and Executive Health
configuration.

- Executive Health
- Action & Risk
- Portfolio / Team

Do not copy private S360, build, incident, owner, or security data into this public example.

Generate the Executive Health site:

```powershell
python ..\..\scripts\build `
  --template executive-health `
  --data canonical-report.json `
  --config executive-health.config.json `
  --output generated\executive-health
```
