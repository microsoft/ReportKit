# Templates

All five built-in templates generate validated report sites from canonical ReportKit data.
Each directory contains a versioned capability contract, design notes, and archived HTML design
prototypes. Use the generated examples for current implementation review:

- [Executive Health](../examples/operational-snapshot/generated/executive-health/index.html)
- [Action & Risk](../examples/operational-snapshot/generated/action-risk/index.html)
- [Portfolio / Team](../examples/operational-snapshot/generated/portfolio-team/index.html)
- [Operational Health](../examples/operational-snapshot/generated/operational-health/index.html)
- [Compliance / Readiness](../examples/operational-snapshot/generated/compliance-readiness/index.html)

These HTML links show source on GitHub; open them locally to review the reports. No Pages
deployment is implied. `_shared/design-system.md` describes the shared visual principles.
The new renderers share layout primitives in `scripts/builtin_renderers.py`; Executive Health
retains its existing renderer in `scripts/reportkit_engine.py`.
