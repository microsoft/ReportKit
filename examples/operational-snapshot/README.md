# Operational Snapshot Demo

This directory contains one synthetic 401-record canonical sample and configurations for all five
built-in templates. Every generated report uses the same source facts, not separate invented
service-availability or compliance-control datasets.

- Executive Health
- Action & Risk
- Portfolio / Team
- Operational Health
- Compliance / Readiness

Do not copy private S360, build, incident, owner, or security data into this public example.

Generate all five sites from the repository root:

```powershell
python -B scripts\build-examples
```

For already-generated ReportKit-owned sample folders, explicitly approve replacement and add
`--overwrite`. Never use that flag to replace unrelated data.

Open `generated\<template-id>\index.html`. Action & Risk includes complete static queues;
Portfolio / Team includes every canonical group's real detail page. Operational and Compliance
show missing domain-specific facts explicitly. All counts retain their source-record units.
