# Shared repository automation

## Project contract

Home Assistant YAML configuration for guarded Sungrow solar curtailment.
Read [README](../README.md), [repository instructions](../AGENTS.md), current source and tests before changing behavior.
Install requirements_test.txt for the fixture tests.
YAML and structural assertions do not prove Home Assistant schema acceptance or inverter commissioning.
Do not restart Home Assistant, write Modbus registers or run device probes.

## Shared checks

This repository uses [Artic0din/reusable-workflows v1.0.0](https://github.com/Artic0din/reusable-workflows/releases/tag/v1.0.0), pinned to `c913ad3e22a42c75bfcf0029448cda48dc546ff1`.
The additional shared-automation workflow checks an explicit list of committed project and agent files.
Existing application workflows retain their own commands, runners, triggers and check names.
File-existence checks establish repository structure, not application correctness or deployment acceptance.
CodeQL, generated-output checks and dependency auto-merge are selected only when their contracts apply; this rollout does not enable privileged behavior.
The library's baseline currently uses chrisreddington/validate-file-exists at its pinned v0.0.10 revision.
Actions policy must permit that exact action and the shared workflow library.
See [workflow contracts](https://github.com/Artic0din/reusable-workflows/blob/c913ad3e22a42c75bfcf0029448cda48dc546ff1/docs/workflow-contracts.md) and [consumer setup](https://github.com/Artic0din/reusable-workflows/blob/c913ad3e22a42c75bfcf0029448cda48dc546ff1/docs/consumer-setup.md).

## Agent skills

- [readme-docs](../.github/skills/readme-docs/SKILL.md)
- [refresh-instructions](../.github/skills/refresh-instructions/SKILL.md)
- [github-actions](../.github/skills/github-actions/SKILL.md)
- [test-gap-audit](../.github/skills/test-gap-audit/SKILL.md)
- [README specialist](../.github/agents/readme-specialist.agent.md)

Existing project-specific instructions and stronger skills remain authoritative.
Selected copied files and their original library revision are recorded in [.github/reusable-skills.json](../.github/reusable-skills.json).
Other existing skills and agents remain repository-owned.

## Validation

Validate changed workflow syntax, managed skill metadata, local links, required files and the final diff for an automation-only update.
Use the repository's existing dependency setup and these source-backed commands when the affected scope requires application checks:

```sh
python -m pytest
```

Only report commands actually run and actual CI conclusions.
Do not infer live device, cloud, tenant or application acceptance from baseline or documentation checks.

## Updates and rollback

Dependabot's github-actions entry proposes versioned workflow-pin updates; merging the library alone does not change this repository's pinned code.
Review and merge each consumer update through its normal PR process.
For a workflow-pin update, update matching version prose and contract links in this guide and skills.
Make those changes in the same PR, including Dependabot PRs.
Do not advance the skill manifest for a workflow-only update.
Its revision records the copied skills' merge base and changes only through a skill update.
Update copied skills separately using the old library source, current tailored file and new library source; preserve local adaptations and resolve conflicts explicitly.
The [skill-update tooling](https://github.com/Artic0din/reusable-workflows/pull/4) is introduced separately; use it after that PR merges.
Onboarding does not install a recurring job or grant a cross-repository credential.
Revert a consumer update commit to restore its prior workflow pins, skill contents and source manifest.
