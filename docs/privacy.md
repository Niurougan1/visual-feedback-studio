# Privacy

Visual Feedback Studio is designed around a local-first workflow.

## Default Storage

By default, browser feedback, preview state, verification state, and optional verification artifacts are written to the reviewed project directory.

The public local workflow does not require a hosted account or default cloud upload.

## Captured Data

The tool may capture reviewer-entered feedback and page context needed to map that feedback back to source:

- Text before and after a reviewer edit
- Style properties selected by the reviewer
- Reviewer annotations
- Element context such as selectors, labels, source hints, and viewport information
- Local workflow status used for preview, apply, and verify steps

Only use the tool on pages and projects where you have permission to capture review context.

## Hosted Workflows

Any hosted, remote, or team workflow should be configured explicitly and reviewed separately. Do not assume that a local project workflow uploads data.

## Sensitive Data

Avoid capturing credentials, private keys, customer data, production secrets, or proprietary information unless your review environment explicitly permits it.

## Contact

For privacy questions, contact the maintainer through the GitHub repository owner profile.
