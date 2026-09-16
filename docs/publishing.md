# Publishing

ReportKit v1 publishers copy a complete validated report folder to a destination.

## Supported destination patterns

- SharePoint or OneDrive synchronized folder
- File share
- GitHub Pages working directory
- Azure DevOps artifact staging directory
- Static storage working directory
- Archive or email-attachment package

## Requirements

A publisher must:

- Confirm that validation has no errors
- Copy the complete site
- Avoid transforming report content
- Avoid partial replacement
- Preserve the previous publication when copying fails
- Report the final destination

Authentication belongs to the destination environment. Credentials never enter canonical data,
generated HTML, manifests, or logs.

