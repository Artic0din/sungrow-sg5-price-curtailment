# Repository agent instructions

Home Assistant YAML configuration for guarded Sungrow solar curtailment.
Use [README.md](README.md) and current committed source for supported behavior.

Use [shared repository automation](docs/shared-automation.md) for selected agent skills, versioned checks and project-specific validation boundaries.

Install requirements_test.txt for the fixture tests.
YAML and structural assertions do not prove Home Assistant schema acceptance or inverter commissioning.
Do not restart Home Assistant, write Modbus registers or run device probes.
