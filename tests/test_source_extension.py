from twinforge.model import (
    ElectronicKey,
    Identity,
    KeyingMode,
    Module,
    SourceExtension,
    SourceNode,
)


def _l5x_extension() -> SourceExtension:
    return SourceExtension(
        format="l5x",
        root=SourceNode(
            name="Module",
            attributes={"Vendor": "1", "FutureAttribute": "keep"},
            children=[
                SourceNode(
                    name="FutureElement",
                    attributes={"PreserveMe": "yes"},
                    text="payload",
                )
            ],
        ),
    )


def test_asset_can_retain_a_recursive_source_snapshot():
    extension = _l5x_extension()
    module = Module(
        name="DI_Slot2",
        slot=2,
        catalog="1756-IB16",
        identity=Identity(),
        source_extensions=[extension],
    )

    retained = module.source_extensions[0]
    assert retained.format == "l5x"
    assert retained.root.attributes["FutureAttribute"] == "keep"
    assert retained.root.children[0].attributes["PreserveMe"] == "yes"
    assert retained.root.children[0].text == "payload"


def test_identity_and_electronic_key_can_retain_independent_source_data():
    module_identity = Identity(source_extensions=[_l5x_extension()])
    key_extension = SourceExtension(
        format="l5x",
        root=SourceNode(name="EKey", attributes={"State": "CompatibleModule"}),
    )
    key = ElectronicKey(
        mode=KeyingMode.COMPATIBLE_MODULE,
        source_extensions=[key_extension],
    )

    assert module_identity.source_extensions[0].root.name == "Module"
    assert key.source_extensions[0].root.name == "EKey"


def test_source_extension_lists_are_not_shared_between_objects():
    first = Identity()
    second = Identity()

    first.source_extensions.append(_l5x_extension())

    assert len(first.source_extensions) == 1
    assert second.source_extensions == []
