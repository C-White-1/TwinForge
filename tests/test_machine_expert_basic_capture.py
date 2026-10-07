"""Machine Expert – Basic `.smbp` capture: roots, retention, limits."""
import pytest

from twinforge.parsers.machine_expert_basic.capture import (
    CaptureLimits, CapturedArtifact, CapturedSection, capture_bytes,
)

BOM = b"\xef\xbb\xbf"
XMLNS = ('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xmlns:xsd="http://www.w3.org/2001/XMLSchema"')


def _smbp(body: str, root: str = "ProjectDescriptor") -> bytes:
    return BOM + f'<?xml version="1.0" encoding="utf-8"?>\r\n<{root} {XMLNS}>{body}</{root}>'.encode()


def _section(captured: CapturedArtifact) -> CapturedSection:
    assert captured.section is not None
    return captured.section


def test_project_root_is_captured_with_original_bytes():
    data = _smbp("<ProjectVersion>2.2.0.0</ProjectVersion><Name>demo</Name>")

    captured = capture_bytes(data, name="demo.smbp")

    assert captured.kind == "project"
    assert captured.raw_bytes == data
    assert _section(captured).tag == "ProjectDescriptor"
    assert [child.tag for child in _section(captured).ordered_children] == ["ProjectVersion", "Name"]
    assert captured.diagnostics == []


def test_encrypted_project_root_is_recognized():
    data = _smbp("<ProjectVersion>2.0.0.0</ProjectVersion><Crypted>AAEC</Crypted>", root="CryptedProject")

    captured = capture_bytes(data)

    assert captured.kind == "encrypted_project"
    crypted = _section(captured).ordered_children[1]
    assert crypted.text == "AAEC"


def test_unknown_elements_and_attributes_are_retained_and_counted():
    data = _smbp('<Name>demo</Name><FutureThing a="1"><Inner/></FutureThing><ProjectVersion x="y"/>')

    captured = capture_bytes(data)

    future = _section(captured).ordered_children[1]
    assert future.tag == "FutureThing" and future.spec is None
    assert future.raw_attributes == {"a": "1"}
    assert [child.tag for child in future.ordered_children] == ["Inner"]
    assert [d.code for d in captured.diagnostics] == ["unclassified_content"]
    # FutureThing + Inner are unclassified elements; a, x are unclassified attributes.
    assert "2 unclassified elements and 2 unclassified attributes" in captured.diagnostics[0].message


def test_unrecognized_root_is_retained_as_xml():
    captured = capture_bytes(b"<project><x/></project>")

    assert captured.kind == "xml"
    assert _section(captured).ordered_children[0].tag == "x"
    assert [d.code for d in captured.diagnostics] == ["unclassified_xml"]


def test_malformed_xml_keeps_bytes_and_reports():
    captured = capture_bytes(b"<ProjectDescriptor>")

    assert captured.kind == "opaque"
    assert captured.section is None
    assert captured.raw_bytes == b"<ProjectDescriptor>"
    assert [d.code for d in captured.diagnostics] == ["xml_capture_error"]


def test_dtd_is_refused():
    data = b'<?xml version="1.0"?><!DOCTYPE ProjectDescriptor [<!ENTITY e "x">]><ProjectDescriptor/>'

    captured = capture_bytes(data)

    assert captured.section is None
    assert [d.code for d in captured.diagnostics] == ["xml_capture_error"]


def test_oversized_input_is_retained_without_inspection():
    data = _smbp("<Name>demo</Name>")

    captured = capture_bytes(data, limits=CaptureLimits(max_input_bytes=10))

    assert captured.section is None
    assert captured.raw_bytes == data
    assert [d.code for d in captured.diagnostics] == ["input_size_limit"]


def test_node_limit_is_enforced():
    captured = capture_bytes(_smbp("<Name/>" * 5), limits=CaptureLimits(max_xml_nodes=3))

    assert captured.section is None
    assert [d.code for d in captured.diagnostics] == ["xml_capture_error"]


def test_limits_must_be_positive():
    with pytest.raises(ValueError):
        CaptureLimits(max_xml_depth=0)
