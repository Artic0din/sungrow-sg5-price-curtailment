---
name: refresh-instructions
description: Refresh a repository's custom instructions against current code and tests while preserving its existing heading structure.
---

# Refresh custom instructions accurately

Read [project automation](../../../docs/shared-automation.md) for this repository's commands and boundaries.

Use this skill when asked to correct existing repository instructions.
Default to .github/copilot-instructions.md when the request does not name a file and that file exists.
If several materially different instruction files could be intended, identify the target before editing.

## Gather evidence

Read the target and record its ordered Markdown headings, including heading levels.
Inspect the actual Git root, branch, current changes, relevant manifests, entrypoints, tests, CI workflows, and referenced documentation.
Use the current checkout as the editing baseline and disclose if the remote differs.
Separate supported behavior from proposed features and historical validation.

## Update within the existing structure

Keep every existing heading's text, level, and order unchanged.
Correct or replace inaccurate content under those headings; add necessary bullets within the existing sections.
Preserve working project-specific constraints and links.
Reference version files and commands that exist; do not guess framework versions or invent npm scripts.
Do not overwrite a project's instructions with a generic template.
Do not edit application code or unrelated policy files.
The requested repository target does not authorize changes to user-wide AGENTS.md or client settings.

## Validate

Compare the ordered headings before and after the change, excluding code fences; they must be identical.
Resolve changed file links, confirm named symbols and script keys, and run relevant checks where needed.
Review the diff for unsupported claims, lost boundaries, and unrelated changes.
Return the corrected facts with their evidence and state any runtime behavior not tested.
