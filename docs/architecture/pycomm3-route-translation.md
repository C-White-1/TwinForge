# pycomm3 Route Translation

`encode_pycomm3_route` is a pure adapter from `CipRouteDeclaration` to the
installed `pycomm3` padded EPATH representation. It constructs no `CIPDriver`,
opens no socket, and performs no discovery request.

The result retains:

- the original typed route declaration;
- the exact encoded EPATH bytes;
- the path with its CIP word-count prefix;
- the calculated word count; and
- the `pycomm3` package name and version.

Byte-level tests cover backplane-style integer links, textual IP-address links,
and raw-byte links. Translation failures do not alter the declaration. The
installed `pycomm3` `PortSegment` implementation represents port numbers and
integer links with one byte and link lengths with one byte. TwinForge reports
an explicit `Pycomm3RouteEncodingError` when a valid declaration exceeds those
adapter limits.

This module is an encoding boundary only. A future routed transport can consume
the encoded path after operator confirmation and request-budget validation.
