from twinforge.model import Identity, VendorIdentity


def test_identity_preserves_numeric_vendor_and_product_type():
    identity = Identity(
        vendor=VendorIdentity(
            id=1,
            name="Allen-Bradley / Rockwell Automation",
        ),
        product_type=7,
        product_type_name="Discrete I/O",
        product_code=11,
    )

    assert identity.vendor is not None
    assert identity.vendor.id == 1
    assert str(identity.vendor) == "Allen-Bradley / Rockwell Automation"
    assert identity.product_type == 7
    assert identity.product_type_name == "Discrete I/O"


def test_unknown_vendor_does_not_require_a_name():
    vendor = VendorIdentity(id=37)

    assert vendor.id == 37
    assert vendor.name is None
    assert str(vendor) == "37"


def test_identity_does_not_invent_missing_values():
    identity = Identity()

    assert identity.vendor is None
    assert identity.product_type is None
    assert identity.product_code is None
    assert identity.revision is None
