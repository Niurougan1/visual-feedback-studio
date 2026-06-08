# Permissions

[简体中文](./permissions.md)

Visual Feedback Studio uses browser permissions to start review on pages selected by the user.

## Chrome Permissions

| Permission | Purpose |
| --- | --- |
| `activeTab` | Allows the extension to act on the current tab after the user clicks it. |
| `scripting` | Injects the review UI into the selected page. |
| `storage` | Saves local preferences and workflow configuration. |
| Optional host access | Lets the user grant repeat access to a specific site. |

## Site Access

Chrome may ask for site access when the extension needs durable access to the current page. Grant access only for pages you are allowed to review.

## File URLs

Chrome requires a separate extension-details setting for `file://` URLs. Enable it only when reviewing local files you control.

## Data Handling

Browser permissions enable local review capture. They do not imply that data is uploaded to a hosted service by default.
