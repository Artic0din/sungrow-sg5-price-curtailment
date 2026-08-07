from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "config" / "packages" / "sungrow_control.yaml"
YAML_PATHS = tuple(
    sorted(
        path
        for directory in ("config", "examples")
        for path in (ROOT / directory).rglob("*.yaml")
    )
)


class HomeAssistantLoader(yaml.SafeLoader):
    """Load Home Assistant YAML while retaining tagged values as strings."""


def _construct_unknown_tag(loader: HomeAssistantLoader, node: yaml.Node) -> Any:
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


HomeAssistantLoader.add_constructor(None, _construct_unknown_tag)


def _load_yaml(path: Path) -> Any:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=HomeAssistantLoader)


def _automations() -> dict[str, dict[str, Any]]:
    package = _load_yaml(PACKAGE_PATH)
    return {automation["id"]: automation for automation in package["automation"]}


def test_all_configuration_files_are_valid_yaml() -> None:
    assert YAML_PATHS
    for path in YAML_PATHS:
        assert _load_yaml(path) is not None, path


def test_automation_ids_are_unique() -> None:
    package = _load_yaml(PACKAGE_PATH)
    identifiers = [automation["id"] for automation in package["automation"]]
    assert len(identifiers) == len(set(identifiers))


def test_inverter_control_uses_documented_register_and_values() -> None:
    automation = _automations()["sungrow_write_run_mode_to_modbus"]
    write_action = automation["action"][0]

    assert write_action["service"] == "modbus.write_register"
    assert write_action["data"]["address"] == 5005
    value_template = write_action["data"]["value"]
    assert "206" in value_template
    assert "207" in value_template


def test_curtailment_keeps_all_safety_guards() -> None:
    automation = _automations()[
        "sungrow_shutdown_when_powerwall_full_and_low_feedin_price"
    ]
    conditions = automation["condition"]

    assert any(
        condition.get("entity_id") == "input_boolean.sungrow_curtailment_enabled"
        and condition.get("state") == "on"
        for condition in conditions
    )
    assert any(
        condition.get("entity_id") == "sensor.inverter_meter_power"
        and condition.get("above") == 100
        for condition in conditions
    )
    assert any(
        condition.get("condition") == "sun"
        and condition.get("after") == "sunrise"
        and condition.get("before") == "sunset"
        for condition in conditions
    )
    assert any(
        condition.get("entity_id") == "input_select.set_sg_inverter_run_mode"
        and condition.get("state") == "Enabled"
        for condition in conditions
    )


def test_restart_requires_shutdown_daylight_and_a_favourable_condition() -> None:
    automation = _automations()["sungrow_restart_when_conditions_favorable"]
    conditions = automation["condition"]

    assert any(
        condition.get("entity_id") == "input_select.set_sg_inverter_run_mode"
        and condition.get("state") == "Shutdown"
        for condition in conditions
    )
    assert any(
        condition.get("condition") == "sun"
        and condition.get("after") == "sunrise"
        and condition.get("before") == "sunset"
        for condition in conditions
    )
    alternatives = next(
        condition["conditions"]
        for condition in conditions
        if condition.get("condition") == "or"
    )
    assert len(alternatives) == 4


def test_sunset_safety_always_reenables_the_inverter() -> None:
    automation = _automations()["sungrow_restart_at_sunset_safety"]
    action = automation["action"][0]

    assert automation["trigger"] == [
        {"platform": "sun", "event": "sunset", "offset": "+00:30:00"}
    ]
    assert action["service"] == "input_select.select_option"
    assert action["data"]["option"] == "Enabled"
