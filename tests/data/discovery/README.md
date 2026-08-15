# Synthetic CIP Discovery Evidence

`cpppo-identity-response.json` is an independently generated, deterministic
response fixture from TwinForge's localhost `cpppo` laboratory. It contains
only the CIP Identity Object response data and its expected interpretation.

The fixture was derived from one bounded Identity class `0x01`, instance
`0x01`, Get Attributes All transaction on 2026-08-15. Wireshark/TShark 4.6.8
independently decoded the response before its promotion into this test fixture.

All network and encapsulation layers were excluded. The fixture therefore
contains no operational address, volatile port, session handle, sender
context, packet timestamp, or unrelated traffic. Its identity values originate
from the tracked deterministic configuration at
`examples/discovery/cpppo_identity_lab.cfg`, not from physical equipment.

The payload SHA-256 authenticates the exact 38 decoded bytes. The test suite
recalculates that checksum and passes the bytes through TwinForge's production
decoder. The source PCAP remains local and ignored.
