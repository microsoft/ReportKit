<!-- BEGIN MICROSOFT SECURITY.MD V1.0.0 BLOCK -->

## Security

Microsoft takes the security of our software products and services seriously, which
includes all source code repositories in our GitHub organizations.

**Please do not report security vulnerabilities through public GitHub issues.**

For security reporting information, locations, contact information, and policies,
please review the latest guidance for Microsoft repositories at
[https://aka.ms/SECURITY.md](https://aka.ms/SECURITY.md).

<!-- END MICROSOFT SECURITY.MD BLOCK -->

# ReportKit security policy

## Reporting vulnerabilities

Do not disclose a suspected vulnerability in a public issue. Report it privately to the repository
maintainers using the private vulnerability-reporting mechanism configured for the hosting
repository.

Include the affected ReportKit version or archive, reproduction steps, expected and observed
behavior, impact, and a minimal sanitized fixture when possible. Do not include real credentials,
customer data, or operational secrets.

Maintainers will acknowledge receipt through the private channel, validate and prioritize the
report, coordinate remediation and disclosure with the reporter, and publish fixes or advisories
when an affected release exists. Do not disclose exploit details publicly before that coordination
is complete.

## Data-handling requirements

ReportKit inputs and outputs may contain operationally sensitive information.

- Never commit credentials, access tokens, secrets, certificates, or connection strings.
- Never copy authentication material into canonical data or provenance.
- Use synthetic or explicitly approved data in public examples.
- Escape all untrusted values before inserting them into HTML.
- Do not make network requests during rendering.
- Do not publish when model or site validation reports an error.
- Display classification and freshness in every generated report.
- Treat generated reports according to their declared classification.

## Supported versions

Security fixes will target the latest released ReportKit version. No released version exists while
the repository remains in implementation-foundation status.
