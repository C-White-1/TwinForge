# cpppo EtherNet/IP Identity Laboratory

## Purpose

This experiment determines whether a localhost `cpppo` EtherNet/IP simulator
can provide reproducible, authorized evidence for TwinForge's bounded
`pycomm3` Identity adapter. The localhost compatibility target was verified on
2026-08-15. It remains a simulator result, not a physical-device compatibility
claim.

The first acceptance target is deliberately narrow:

- establish and close an EtherNet/IP explicit-messaging session;
- obtain List Identity or Identity Object evidence;
- preserve the request, response, provider version, and capture context;
- compare TwinForge decoding with Wireshark; and
- complete without tag writes, attribute writes, fuzzing, or boundary scans.

## External research source

The laboratory design was prompted by
[404saint/industrial-protocol-labs](https://github.com/404saint/industrial-protocol-labs),
particularly its
[EtherNet/IP research lab](https://github.com/404saint/industrial-protocol-labs/tree/main/ethernet-ip%20research)
and
[laboratory reproduction guide](https://github.com/404saint/industrial-protocol-labs/blob/main/ethernet-ip%20research/notes/13-lab-reproduction-guide.md).

Source metadata observed on 2026-08-15:

- repository created on 2026-06-16;
- default branch `main`;
- Apache-2.0 repository licence;
- EtherNet/IP research introduced by commit
  `14743843d36775405c9d189e7f6e947e39567a7e` on 2026-06-29;
- simulator identified as `cpppo` on TCP port 44818 over loopback; and
- an `ethernet_ip_lab.pcap` file reported as 20,480 bytes with Git blob ID
  `f755af0410e3e2a5f7e38a01b473d50088f230d9`.

A Git blob ID is repository identity evidence, not a substitute for recording
the downloaded file's SHA-256 checksum. TwinForge has not copied or vendored
the external capture.

## Upstream evidence boundary

The source is useful laboratory guidance but is not treated as an
authoritative EtherNet/IP specification or a drop-in implementation.

Observed review issues include:

- several scripts described as low-level protocol work use the higher-level
  `cpppo` client API;
- the passive monitor searches payload bytes for the ANSI symbolic segment
  marker instead of fully decoding EtherNet/IP, CPF, and CIP layers;
- the monitor catches broad exceptions without retaining diagnostics;
- dependencies and simulator versions are not pinned in the repository root;
- some EtherNet/IP note filenames retain Modbus-oriented names; and
- the documented Read Tag Single experiment describes service `0x4C`, while
  its captured response begins with `0xD2`, the response form of service
  `0x52`. The complete request and routing context must be decoded before that
  transaction can be classified.

These issues do not invalidate the laboratory concept. They mean TwinForge
must reproduce and independently decode observations rather than importing
the upstream conclusions.

## Safety boundary

The initial experiment is limited to a simulator bound to localhost or an
equivalent isolated container network owned by the operator.

The procedure must:

- bind the simulator so it is not reachable from external interfaces;
- declare `127.0.0.1` or the isolated container endpoint explicitly;
- use the existing TwinForge authorization, confirmation, timeout, pacing,
  and request-budget controls;
- record exact `cpppo`, `pycomm3`, Python, Wireshark, and TwinForge versions;
- retain failed and malformed responses as diagnostics;
- avoid using public addresses or automatic target discovery; and
- stop after the allowed identity operations.

The following upstream capabilities are out of scope:

- symbolic or object-attribute writes;
- fragmented writes;
- capability or address-space boundary enumeration;
- deliberately induced faults beyond a documented invalid read-only request;
- replay, fuzzing, denial-of-service, or mode changes; and
- testing against production equipment.

## Proposed procedure

### Gate 1: reproducible simulator

1. Record the selected `cpppo` release and its licence.
2. Create a local configuration containing deterministic synthetic identity
   values and no site-derived names, addresses, or serial numbers.
3. Bind TCP port 44818 to localhost only.
4. Confirm the listening endpoint before starting TwinForge.
5. Record startup configuration and a SHA-256 checksum for every retained
   fixture.

TwinForge pins `cpppo==5.2.5` in the optional `cip-sim` dependency group. The
package is dual-licensed under GPL-3.0-or-later or a commercial licence; it is
therefore isolated from TwinForge's runtime dependencies and is not vendored.
Install the laboratory dependency explicitly:

```powershell
uv sync --group cip-sim
```

Start the deterministic synthetic simulator from the repository root:

```powershell
uv run --group cip-sim python `
  examples/discovery/run_cpppo_identity_lab.py
```

The launcher clears cpppo's ambient configuration search list before loading
only `cpppo_identity_lab.cfg`. This is necessary because cpppo 5.2.5's
`--config-basename` changes its configuration name but does not rebuild the
already initialized search list. The launcher binds TCP to loopback only and
disables the additional UDP listener. In a second terminal, make the one
authorized request through TwinForge's actual adapter:

```powershell
uv run twinforge discover identity 127.0.0.1 `
  --engagement "TwinForge localhost cpppo identity laboratory" `
  --authorization-reference "operator laboratory approval" `
  --execute `
  --output cpppo-identity-snapshot.json
```

Omitting `--execute` exits before constructing the provider or opening a
socket. The output path is intentionally operator-selected; live evidence is
not a checked-in fixture until Gate 4 review is complete.

### Gate 1 result

Gate 1 completed successfully on 2026-08-15 with `cpppo==5.2.5` and
`pycomm3==1.2.16`. TwinForge made one unconnected Identity Object
`Get_Attributes_All` request and observed the configured synthetic values:

| Field | Observed value |
| --- | --- |
| Vendor ID | `0` |
| Device type | `0` |
| Product code | `4242` |
| Revision | `1.2` |
| Status | `0` |
| Serial number | `305419896` (`0x12345678`) |
| Product name | `TwinForge cpppo Lab` |
| State | `3` |

The observation retained the Identity payload, encapsulated raw reply, three
trailing payload bytes, adapter version, service, class, instance, and request
number. The fixture SHA-256 is
`5a2a132a022fda4f08277c8ce0dc4d73692ab0d7033bed3cef7efce2b9f85d97`.

Two negative observations were also retained during setup:

- cpppo's packaged default Identity was returned when its
  `--config-basename` option failed to replace the initialized search list;
  the dedicated launcher now clears that list; and
- hexadecimal integer text in the INI file caused cpppo to close the session;
  the fixture now uses decimal values accepted by `ConfigParser.getint`.

This verifies the reproducible simulator and TwinForge adapter interaction.

The installed TwinForge CLI was also verified through both paths:

- without `--execute`, it emitted the exact one-request dry-run plan and made
  no connection; and
- with `--execute`, it returned the configured identity and retained raw
  response evidence.

### Gate 2 status

Gate 2 completed successfully on 2026-08-15 with Wireshark/TShark 4.6.8 and
Npcap 1.88. TShark captured the transaction from the explicit
`\Device\NPF_Loopback` interface. Selecting the interface by name avoided the
unstable numeric interface ordering observed between elevated and ordinary
processes.

The local, uncommitted capture contained 17 packets over approximately 32 ms:

| Frame | Direction | Decoded operation |
| ---: | --- | --- |
| 1-3 | Client/server | TCP session establishment |
| 4 | Client to server | EtherNet/IP Register Session (`0x0065`) |
| 6 | Server to client | Successful Register Session response |
| 8 | Client to server | SendRRData with Get Attributes All request |
| 10 | Server to client | Successful Get Attributes All response |
| 12 | Client to server | EtherNet/IP Unregister Session (`0x0066`) |
| 13-17 | Client/server | TCP acknowledgement and teardown |

Wireshark independently decoded frame 8 as an unconnected CPF transaction
containing a Null Address Item and an Unconnected Data Item. Its CIP request
path was Identity class `0x01`, instance `0x01`. Frame 10 returned no
additional-status words and decoded the same synthetic values retained by
TwinForge: vendor ID `0`, device type `0`, product code `4242`, revision
`1.2`, status `0`, serial number `0x12345678`, product name
`TwinForge cpppo Lab`, and operational state `3`.

The independent decode also identified the three bytes preserved by TwinForge
after the primary identity fields. They encode Configuration Consistency Value
`0x0000` and Heartbeat Interval `0x00`, Identity attributes 9 and 10. Retaining
the original bytes alongside their dedicated optional model fields protects
against truncated or future-extended Identity responses.

The capture was 1,988 bytes with SHA-256
`02280c1dfd54d857bf46063991495fa2bb3ffc8a443c85fdf6cba3bb792f6247`.
It contains only loopback endpoints and deterministic synthetic values, but it
remains ignored as `.cpppo-gate2.pcapng` pending the Gate 4 provenance,
redistribution, and fixture review.

For future reproduction, enumerate interfaces with the full executable path
because Wireshark is not necessarily on `PATH`:

```powershell
& "C:\Program Files\Wireshark\tshark.exe" -D
```

Capture by stable interface name, restrict the capture to TCP port 44818, run
one `twinforge discover identity ... --execute` command, and stop after that
transaction:

```powershell
& "C:\Program Files\Wireshark\tshark.exe" `
  -i "\Device\NPF_Loopback" `
  -f "tcp port 44818" `
  -w .cpppo-gate2.pcapng
```

The resulting capture must still be reviewed before it is considered for Gate
4 or committed to the repository.

### Gate 4 result

Gate 4 promoted only the 38-byte CIP Identity response data, not the PCAP. The
tracked
[`cpppo-identity-response.json`](../../tests/data/discovery/cpppo-identity-response.json)
fixture records its provenance, sanitization boundary, SHA-256, expected
identity fields, and independently decoded optional trailing attributes.

The extraction removed the EtherNet/IP encapsulation header, CPF framing, TCP
and IP layers, session handle, sender context, ports, timing, and capture
metadata. The retained values are deterministic synthetic values from the
tracked simulator configuration. An offline regression test authenticates the
payload checksum and passes the exact bytes through TwinForge's production
decoder. The source PCAP remains ignored.

### Gate 2: independent protocol baseline

1. Capture simulator startup and one known-good identity transaction.
2. Decode the encapsulation header, CPF items, CIP service, path, general
   status, additional status, and returned fields with Wireshark.
3. Record whether the simulator implements List Identity, routed Identity, or
   only explicit Identity Object attributes.
4. Keep simulator-specific behavior distinct from ODVA-defined behavior.

### Gate 3: TwinForge adapter validation

1. Run the existing dry-run or operator-confirmation path.
2. Execute only the minimum permitted identity capability.
3. Confirm that request budgets and pacing are enforced.
4. Compare the retained TwinForge observation with the packet capture.
5. Verify vendor ID, device type, product code, revision, status, serial
   number, and product name only when each field is actually returned.
6. Preserve unsupported operations, missing attributes, and malformed replies
   as diagnostics rather than empty values.

### Gate 4: sanitized regression evidence

Only after successful independent review:

1. create the smallest independently generated capture or response fixture;
2. remove volatile session handles and synthetic identifiers only through a
   documented sanitization process;
3. record provenance, versions, capture point, licence, and SHA-256;
4. verify redistribution and sensitivity under the artifact policy; and
5. add deterministic offline regression tests without requiring a live
   simulator in CI.

## Acceptance criteria

The Phase 2 roadmap item may be marked verified only when:

- the simulator configuration and versions are reproducible;
- TwinForge completes a bounded identity capture against localhost;
- captured packets independently support the decoded observation;
- no write or enumeration capability is exercised;
- raw and unknown response evidence is retained where available;
- failure cases remain visible as diagnostics; and
- the full TwinForge quality suite remains green.

Successful `cpppo` testing establishes simulator compatibility only. It does
not establish compatibility with a physical Logix controller, routed chassis,
or other vendor's EtherNet/IP implementation.
