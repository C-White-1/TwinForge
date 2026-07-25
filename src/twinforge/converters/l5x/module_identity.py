"""Identity and electronic-key conversion for captured L5X modules."""

from __future__ import annotations

from collections.abc import Mapping

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    ElectronicKey,
    Identity,
    KeyingMode,
    Revision,
    VendorIdentity,
)
from twinforge.parsers.l5x.capture import CapturedSection
from twinforge.schema.l5x.modules import EKEY_ATTRIBUTES
from twinforge.schema.l5x.spec import AttributeSpec

from .conversion_value import emit_diagnostic, optional_int
from .source_extension import captured_to_source_extension


_KEYING_MODES = {
    "CompatibleModule": KeyingMode.COMPATIBLE_MODULE,
    "ExactMatch": KeyingMode.EXACT_MATCH,
    "Disabled": KeyingMode.DISABLED,
    "Custom": KeyingMode.CUSTOM,
}


def convert_identity(
    section: CapturedSection,
    specs: Mapping[str, AttributeSpec],
    diagnostics: list[ConversionDiagnostic] | None,
    *,
    diagnostic_owner: CapturedSection | None = None,
) -> Identity:
    """Convert CIP identity attributes while retaining unresolved numeric IDs."""

    owner = diagnostic_owner or section
    vendor_id = optional_int(
        section.attributes.get("Vendor"), "Vendor", owner, diagnostics
    )
    major = optional_int(
        section.attributes.get("Major"), "Major", owner, diagnostics
    )
    minor = optional_int(
        section.attributes.get("Minor"), "Minor", owner, diagnostics
    )
    revision = (
        Revision(major, minor)
        if major is not None and minor is not None
        else None
    )
    vendor_name = (
        _value_label(specs.get("Vendor"), vendor_id)
        if vendor_id is not None
        else None
    )
    if vendor_id is not None and vendor_name is None:
        emit_diagnostic(
            diagnostics,
            DiagnosticSeverity.INFO,
            "unknown_vendor",
            f"vendor ID {vendor_id} has no resolved name",
            owner,
            "Vendor",
            str(vendor_id),
        )
    if (major is None) != (minor is None):
        emit_diagnostic(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "incomplete_revision",
            "identity revision requires both Major and Minor values",
            owner,
        )

    return Identity(
        vendor=(
            VendorIdentity(vendor_id, vendor_name)
            if vendor_id is not None
            else None
        ),
        product_type=optional_int(
            section.attributes.get("ProductType"),
            "ProductType",
            owner,
            diagnostics,
        ),
        product_code=optional_int(
            section.attributes.get("ProductCode"),
            "ProductCode",
            owner,
            diagnostics,
        ),
        revision=revision,
    )


def convert_electronic_key(
    module: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> ElectronicKey | None:
    """Convert the first documented EKey and preserve its captured source."""

    sections = module.elements.get("EKey", [])
    if not sections:
        return None

    section = sections[0]
    state = section.attributes.get("State")
    mode = _KEYING_MODES.get(state) if state is not None else None
    unknown_mode = state if state is not None and mode is None else None
    if unknown_mode is not None:
        emit_diagnostic(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "unknown_keying_mode",
            (
                f"module {module.attributes.get('Name', '')!r} uses "
                f"unknown EKey state {state!r}"
            ),
            module,
            "State",
            state,
        )

    identity = None
    identity_fields = ("Vendor", "ProductType", "ProductCode", "Major", "Minor")
    if any(name in section.attributes for name in identity_fields):
        identity = convert_identity(
            section,
            EKEY_ATTRIBUTES,
            diagnostics,
            diagnostic_owner=module,
        )
        identity.source_extensions.append(captured_to_source_extension(section))

    if mode is KeyingMode.CUSTOM:
        missing = [
            name for name in identity_fields if name not in section.attributes
        ]
        if missing:
            emit_diagnostic(
                diagnostics,
                DiagnosticSeverity.WARNING,
                "incomplete_custom_ekey",
                f"custom EKey is missing: {', '.join(missing)}",
                module,
            )

    return ElectronicKey(
        mode=mode,
        identity=identity,
        unknown_mode=unknown_mode,
        source_extensions=[captured_to_source_extension(section)],
    )


def _value_label(spec: AttributeSpec | None, value: int) -> str | None:
    """Resolve a specification label without treating it as source identity."""

    if spec is None:
        return None
    for known_value, label in spec.value_labels:
        if known_value == value:
            return label
    return None
