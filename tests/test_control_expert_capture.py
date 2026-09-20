"""Independent fixtures for the provisional read-only capture boundary."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import warnings
import zipfile

import pytest

from twinforge.parsers.control_expert import CaptureLimits, capture_bytes, capture_file
from twinforge.schema.control_expert import ElementSpec


def archive(*entries: tuple[str, bytes]) -> bytes:
    stream = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for name, data in entries:
                output.writestr(name, data)
    return stream.getvalue()


def test_nested_capture_preserves_bytes_duplicates_paths_and_opaque_members():
    xml = b'<FEFExchangeFile><program><STSource>x := 1;</STSource></program></FEFExchangeFile>'
    zef = archive(("DTM/", b""), ("unitpro.xef", xml),
                  ("unitpro.xef", b"<Other/>"), ("../unknown.bin", b"\x00\xff"))
    original = archive(("sample.zef", zef), ("standalone.xef", b"<Different/>"))
    result = capture_bytes(original, name="samples.zip")
    assert result.raw_bytes == original
    nested = result.members[0]
    assert nested.raw_bytes == zef
    assert [m.name for m in nested.members] == ["DTM/", "unitpro.xef", "unitpro.xef", "../unknown.bin"]
    assert nested.members[0].directory
    assert nested.members[1].raw_bytes == xml
    assert nested.members[1].sha256 == sha256(xml).hexdigest()
    assert nested.members[1].source.members == ((0, "sample.zef"), (1, "unitpro.xef"))
    assert nested.members[2].source != nested.members[1].source
    assert nested.members[3].raw_bytes == b"\x00\xff"
    assert result.members[1].section is not None
    assert result.members[1].section.tag == "Different"


def test_xml_order_namespaces_comments_text_and_unknown_attributes():
    data = (b'<FEFExchangeFile xmlns:v="urn:vendor" extra="yes">before'
            b'<!--note--><program><STSource> a &lt; b; </STSource></program>tail'
            b'<?hint keep?><v:future v:key="value"><v:child/>text</v:future>'
            b'<program/></FEFExchangeFile>')
    result = capture_bytes(data, name="source.xef")
    section = result.section
    assert section is not None
    assert section.extra_attributes == {"extra": "yes"}
    assert section.text == "before"
    assert [c.tag for c in section.ordered_children] == [
        "#comment", "program", "#processing-instruction", "{urn:vendor}future", "program"]
    assert section.ordered_children[1].tail == "tail"
    assert section.ordered_children[1].ordered_children[0].text == " a < b; "
    future = section.ordered_children[3]
    assert future.spec is None
    assert future.raw_attributes == {"{urn:vendor}key": "value"}
    assert future.ordered_children[0].tail == "text"
    assert result.raw_bytes == data


def test_specification_controls_classification():
    spec = ElementSpec("Custom", frozenset({"known"}), (ElementSpec("Item"),))
    result = capture_bytes(b'<Custom known="1" other="2"><Item/><Future/></Custom>',
                           name="test.xef", spec=spec)
    assert result.section is not None
    assert result.section.spec == spec
    assert result.section.extra_attributes == {"other": "2"}
    assert result.section.ordered_children[0].spec == spec.children[0]
    assert result.section.ordered_children[1].spec is None


@pytest.mark.parametrize("data", [
    b'<!DOCTYPE FEFExchangeFile [<!ENTITY x "expanded">]><FEFExchangeFile>&x;</FEFExchangeFile>',
    '<!DOCTYPE FEFExchangeFile SYSTEM "file:///not-read"><FEFExchangeFile/>'.encode("utf-16"),
    b'<FEFExchangeFile><broken>',
])
def test_unsafe_or_malformed_xml_retains_original_with_diagnostic(data: bytes):
    result = capture_bytes(data, name="bad.xef")
    assert result.raw_bytes == data
    assert result.section is None
    assert result.diagnostics[0].code == "xml_capture_error"


def test_depth_and_expansion_limits_preserve_archive():
    nested = archive(("project.zef", archive(("unitpro.xef", b"<FEFExchangeFile/>"))))
    result = capture_bytes(nested, limits=CaptureLimits(max_archive_depth=1))
    assert result.members[0].raw_bytes is not None
    assert result.members[0].diagnostics[0].code == "archive_depth_limit"
    limited = capture_bytes(archive(("large.bin", b"x" * 100), ("small.bin", b"ok")),
                            limits=CaptureLimits(max_member_bytes=10))
    assert limited.members[0].raw_bytes is None
    assert limited.members[0].diagnostics[0].code == "expanded_size_limit"
    assert limited.members[1].raw_bytes == b"ok"
    assert limited.raw_bytes is not None


def test_aggregate_budget_and_member_count():
    data = archive(("a", b"1234"), ("b", b"5678"), ("c", b"9"))
    result = capture_bytes(data, limits=CaptureLimits(max_expanded_bytes=5))
    assert result.members[0].raw_bytes == b"1234"
    assert result.members[1].raw_bytes is None
    assert result.members[2].raw_bytes == b"9"
    count_limited = capture_bytes(data, limits=CaptureLimits(max_members=1))
    assert len(count_limited.members) == 1
    assert count_limited.diagnostics[0].code == "member_count_limit"
    assert count_limited.raw_bytes == data


def test_corrupt_archive_and_xml_complexity_are_explicit():
    broken = capture_bytes(b"not a zip", name="broken.zef")
    assert broken.diagnostics[0].code == "archive_read_error"
    for limits in [CaptureLimits(max_xml_depth=2), CaptureLimits(max_xml_nodes=2)]:
        result = capture_bytes(b"<a><b><c/></b></a>", name="deep.xml", limits=limits)
        assert result.section is None
        assert result.diagnostics[0].code == "xml_capture_error"


def test_input_limit_leaves_file_unchanged(tmp_path: Path):
    path = tmp_path / "source.zef"
    data = b"original"
    path.write_bytes(data)
    with pytest.raises(ValueError, match="max_input_bytes"):
        capture_file(path, limits=CaptureLimits(max_input_bytes=2))
    assert path.read_bytes() == data
    result = capture_bytes(data, limits=CaptureLimits(max_input_bytes=2))
    assert result.raw_bytes == data
    assert result.diagnostics[0].code == "input_size_limit"


def test_local_samples_when_available():
    folder = Path(__file__).resolve().parents[1] / "reference" / "control-expert"
    paths = sorted(folder.glob("*.zip"))
    if not paths:
        pytest.skip("Local Control Expert reference archives are not installed")
    for path in paths:
        result = capture_file(path)
        assert not result.diagnostics
        projects = [m for m in result.members if m.name.lower().endswith(".zef")]
        assert projects
        for project in projects:
            assert not project.diagnostics
            xefs = [m for m in project.members if m.name.lower().endswith(".xef")]
            assert xefs
            for xef in xefs:
                assert all(d.code == "unclassified_content" for d in xef.diagnostics)
                assert xef.section is not None
                assert xef.section.tag == "ZEFExchangeFile"


@pytest.mark.parametrize("root", ["FEFExchangeFile", "ZEFExchangeFile"])
def test_exchange_roots_classified_without_changing_identity(root: str):
    result = capture_bytes(f'<{root}><fileHeader DTDVersion="future"/></{root}>'.encode(),
                           name="project.xef")
    assert result.section is not None
    assert result.section.spec is not None
    assert result.section.tag == root
    assert result.section.ordered_children[0].raw_attributes["DTDVersion"] == "future"


def test_encrypted_member_is_retained_in_parent_without_empty_success():
    data = bytearray(archive(("secret.bin", b"original")))
    # Set encryption flags in both headers without needing an encryption library.
    import struct
    central = data.index(b"PK\x01\x02")
    struct.pack_into("<H", data, 6, 1)
    struct.pack_into("<H", data, central + 8, 1)
    result = capture_bytes(bytes(data))
    assert result.raw_bytes == bytes(data)
    assert result.members[0].raw_bytes is None
    assert result.members[0].diagnostics[0].code == "encrypted_member"


def test_crc_failure_does_not_discard_other_members():
    import struct
    data = bytearray(archive(("bad.bin", b"payload"), ("good.bin", b"retained")))
    central = data.index(b"PK\x01\x02")
    struct.pack_into("<I", data, central + 16, 0)
    result = capture_bytes(bytes(data))
    assert result.members[0].diagnostics[0].code == "member_read_error"
    assert result.members[0].raw_bytes is None
    assert result.members[1].raw_bytes == b"retained"
    assert result.raw_bytes == bytes(data)


def test_unknown_content_has_coverage_diagnostic_with_source_location():
    result = capture_bytes(b'<ZEFExchangeFile newer="1"><Future/></ZEFExchangeFile>',
                           name="project.xef")
    assert result.diagnostics[0].code == "unclassified_content"
    assert result.diagnostics[0].source.xml_path == "/ZEFExchangeFile"
