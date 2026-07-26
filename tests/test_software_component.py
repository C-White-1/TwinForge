import pytest

from twinforge.model import (
    AddOnInstruction,
    Device,
    DeviceType,
    Identity,
    Module,
    SoftwareBinding,
    SoftwareBindingRole,
    SoftwareComponent,
    SoftwareComponentKind,
    Tag,
)


def _powerflex_objects():
    instruction = AddOnInstruction(name="Dvc_PF525")
    component = SoftwareComponent(
        name="Dvc_PF525",
        kind=SoftwareComponentKind.FUNCTION_BLOCK,
        implementation=instruction,
        vendor="Jeremy Medders",
        revision="1.0",
    )
    device = Device(
        name="PowerFlex 525",
        device_type=DeviceType.DRIVE,
    )
    module = Module(
        name="Dev_PF525",
        catalog="ETHERNET-MODULE",
        identity=Identity(),
    )
    instance = Tag(name="Dvc", data_type="Dvc_PF525")
    return component, instruction, device, module, instance


def test_powerflex_definition_binds_device_module_and_instance_tag():
    component, instruction, device, module, instance = _powerflex_objects()

    component.bind_device(
        device,
        evidence="Dvc_PF525 AOI description identifies PowerFlex 525",
    )
    component.bind_module(
        module,
        evidence="Dvc_PF525 call receives Dev_PF525 MODULE argument",
    )
    component.bind_tag(
        instance,
        role=SoftwareBindingRole.INSTANCE_TAG,
        evidence="Dvc tag has datatype Dvc_PF525",
    )

    assert component.implementation is instruction
    assert [binding.target for binding in component.bindings] == [
        device,
        module,
        instance,
    ]
    assert component.bindings[2].role is SoftwareBindingRole.INSTANCE_TAG
    assert all(binding.parent is component for binding in component.bindings)
    assert device.parent is None
    assert module.parent is None
    assert instance.parent is None


def test_one_definition_can_bind_multiple_device_instances():
    component, _, device, _, instance = _powerflex_objects()
    second_device = Device(name="Fan Drive", device_type=DeviceType.DRIVE)
    second_instance = Tag(name="FanDvc", data_type="Dvc_PF525")

    component.bind_device(device, evidence="compressor drive evidence")
    component.bind_tag(
        instance,
        role=SoftwareBindingRole.INSTANCE_TAG,
        evidence="compressor instance evidence",
        metadata={"device": device.name},
    )
    component.bind_device(second_device, evidence="fan drive evidence")
    component.bind_tag(
        second_instance,
        role=SoftwareBindingRole.INSTANCE_TAG,
        evidence="fan instance evidence",
        metadata={"device": second_device.name},
    )

    assert len(component.bindings) == 4
    assert component.bindings[1].metadata["device"] == "PowerFlex 525"
    assert component.bindings[3].metadata["device"] == "Fan Drive"


def test_binding_requires_evidence_and_matching_target_type():
    component, _, device, _, _ = _powerflex_objects()

    with pytest.raises(ValueError, match="evidence"):
        component.bind_device(device, evidence="")

    with pytest.raises(TypeError, match="requires Tag"):
        component.add_binding(
            SoftwareBinding(
                target=device,
                role=SoftwareBindingRole.INSTANCE_TAG,
                evidence="invalid target deliberately tested",
            )
        )
