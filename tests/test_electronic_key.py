from twinforge.model import (
    ElectronicKey,
    Identity,
    KeyingMode,
    Module,
    Revision,
    VendorIdentity,
)


def test_module_and_custom_key_keep_separate_identities():
    module_identity = Identity(
        vendor=VendorIdentity(1, "Allen-Bradley / Rockwell Automation"),
        product_type=7,
        product_code=11,
        revision=Revision(3, 1),
    )
    key_identity = Identity(
        vendor=VendorIdentity(37),
        product_type=12,
        product_code=42,
        revision=Revision(1, 5),
    )
    module = Module(
        name="DI_Slot2",
        slot=2,
        catalog="1756-IB16",
        identity=module_identity,
        electronic_key=ElectronicKey(
            mode=KeyingMode.CUSTOM,
            identity=key_identity,
        ),
    )

    assert module.identity.vendor == VendorIdentity(
        1, "Allen-Bradley / Rockwell Automation"
    )
    assert module.electronic_key is not None
    assert module.electronic_key.identity is key_identity
    assert module.electronic_key.identity is not None
    assert module.electronic_key.identity.vendor == VendorIdentity(37)


def test_compatible_key_does_not_require_an_identity():
    key = ElectronicKey(mode=KeyingMode.COMPATIBLE_MODULE)

    assert key.identity is None


def test_unknown_keying_mode_is_preserved():
    key = ElectronicKey(unknown_mode="FutureKeyingMode")

    assert key.mode is None
    assert key.unknown_mode == "FutureKeyingMode"
