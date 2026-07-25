import pytest

from twinforge.exporters import AutomationMLValidationError
from twinforge.exporters.automationml_identity import deterministic_id
from twinforge.exporters.automationml_reference_validation import (
    validate_automationml_references,
)
from twinforge.exporters.automationml_types import CAEX_NAMESPACE


def test_deterministic_identity_uses_kind_and_logical_path():
    first = deterministic_id("element", "system/PLC/module/1")

    assert first == deterministic_id("element", "system/PLC/module/1")
    assert first != deterministic_id("interface", "system/PLC/module/1")
    assert first != deterministic_id("element", "system/PLC/module/2")


def test_semantic_validation_rejects_duplicate_caex_ids(tmp_path):
    xml = f"""
    <CAEXFile xmlns="{CAEX_NAMESPACE}">
      <InstanceHierarchy Name="Example">
        <InternalElement Name="One" ID="duplicate" />
        <InternalElement Name="Two" ID="duplicate" />
      </InstanceHierarchy>
    </CAEXFile>
    """

    with pytest.raises(
        AutomationMLValidationError,
        match="duplicate CAEX IDs",
    ):
        validate_automationml_references(xml, tmp_path / "example.aml")
