# Publishing

This is the target v1 publishing contract, not an implemented command. No publisher or Pages
deployment is implemented. Today, return validated local files or give manual copy instructions;
do not copy to a destination without explicit approval for the exact artifact and destination.

A future ReportKit v1 publisher copies a complete validated report folder to a destination.

## Planned destination patterns

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
