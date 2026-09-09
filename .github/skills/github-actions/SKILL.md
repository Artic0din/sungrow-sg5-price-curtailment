---
name: github-actions
description: Maintain sungrow-sg5-price-curtailment's GitHub Actions callers and existing validation without changing its application or deployment contract.
---

# Maintain repository automation

Read [project automation](../../../docs/shared-automation.md), the current workflow and repository instructions before editing.
Use the [pinned shared workflow contract](https://github.com/Artic0din/reusable-workflows/blob/ad2f70ec9dbf008652223e77424e9b329c835ad1/docs/workflow-contracts.md) for supported inputs and permissions.
Home Assistant YAML configuration for guarded Sungrow solar curtailment.

## Implement

Keep each existing application check, event, runner requirement and protected check context.
Use read-only permissions and full commit pins with release comments for shared checks.
Keep Copilot setup, dependency ecosystems and application build commands local.
Do not enable CodeQL, dependency auto-merge, deployment or production writes unless separately authorised.
Install requirements_test.txt for the fixture tests.
YAML and structural assertions do not prove Home Assistant schema acceptance or inverter commissioning.
Do not restart Home Assistant, write Modbus registers or run device probes.

## Validate

Validate changed workflow YAML with actionlint and applicable repository checks.
Check selected skill metadata and local links; run git diff --check and staged/outgoing Gitleaks scans before publishing.
Use the commands documented in project automation for the affected application scope, with the repository's locked dependencies.
Inspect actual GitHub results and preserve failure propagation; parsing YAML does not prove runtime or live-service acceptance.
