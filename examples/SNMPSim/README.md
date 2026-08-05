# TwinForge Local SNMP Simulator

This fixture represents a fictional managed switch. It contains sanitized
system, interface, IP-address, bridge-forwarding and LLDP evidence. It was
written for TwinForge and contains no capture from an operational network.

The simulator is intentionally bound to the IPv4 loopback interface on
unprivileged UDP port `1161`. Nothing in this example scans a network.

## Fixture identity

- Endpoint: `127.0.0.1:1161`
- SNMP version for the first experiment: v2c
- Read-only community: `twinforge-switch`
- Simulated management address in evidence: `192.0.2.60`
- Simulated LLDP neighbour: `PLC-LAB-01`

The `192.0.2.0/24` network is used only as documentation data inside the
recording. The simulator does not bind to that address.

## Installation

Do not install this merely to run TwinForge's unit tests. The existing tests
use an in-memory fake provider and require no simulator.

The repository defines optional client and simulator dependency groups. When
ready for the interactive experiment, synchronize them:

```powershell
uv sync --extra snmp --group snmp-sim
```

This keeps the simulator out of TwinForge's runtime dependencies.

## Start the local responder

From the repository root, use the Windows-safe launch script:

```powershell
examples\SNMPSim\start_loopback.ps1
```

Keep that terminal open while testing. Stop the responder with `Ctrl+C`.

The script resolves the data directory to an absolute path and gives SNMPSim
an explicit temporary cache directory. This avoids a Windows DBM path problem
encountered with relative data directories.

In a second terminal, capture the simulated switch through TwinForge:

```powershell
uv run --extra snmp python examples/SNMPSim/capture_loopback.py --summary
```

The command uses SNMPv3 by default and prints a short evidence summary. Omit
`--summary` to print the complete Discovery Snapshot JSON. It does not write
credentials or evidence to disk. Use `--version 2c` only when troubleshooting
the local baseline.

To print evidence-backed topology candidates instead of the raw snapshot:

```powershell
uv run --extra snmp python examples/SNMPSim/capture_loopback.py --topology
```

The topology output distinguishes a protocol-reported LLDP neighbour from
indirect MAC reachability. A forwarding entry corroborates an LLDP link only
when its MAC and explicitly resolved interface agree.

The `.snmprec` filename supplies the v1/v2c community name. Consequently,
`twinforge-switch.snmprec` is queried using community `twinforge-switch`.

## Security note

SNMPv2c is used only to make the first loopback experiment observable and
easy to troubleshoot. It must not become TwinForge's recommended deployment
configuration. A later experiment will use SNMPv3 authentication and privacy.

Do not change the responder endpoint to `0.0.0.0`, a LAN address, or a public
address without an explicit test plan and authorization.

## Next implementation step

TwinForge uses an offline `SnmprecDiscoveryProvider` to exercise recording
parsing and evidence lowering without opening a socket. The live client uses
the maintained PySNMP 7.1 API behind the existing `SnmpDiscoveryProvider`
protocol. PySNMP remains optional rather than becoming a core dependency.

The initial `PySnmpLoopbackDiscoveryProvider` is restricted to:

- the loopback endpoint above;
- read operations;
- an allowlist of system, interface, IP, bridge and LLDP OIDs;
- bounded timeouts and request counts; and
- raw OID evidence retention.

The loopback experiment has been verified against the checked-in fixture.
SNMPv3 and an authorized managed switch will be evaluated separately.

## External recording corpus

Published recordings should normally remain outside the repository. Describe
each local file in a JSON manifest containing its source URL, licence, device
category, sanitisation status and optional SHA-256 checksum. The example
manifest demonstrates the format without introducing third-party evidence.

Measure a corpus entirely offline with:

```powershell
uv run python examples/SNMPSim/measure_corpus.py `
  examples/SNMPSim/corpus.example.json `
  reports/snmp-corpus.md
```

For a downloaded external directory, first create a reviewable manifest:

```powershell
uv run python examples/SNMPSim/inventory_corpus.py PATH_TO_DATA corpus.json `
  --source-url https://docs.lextudio.com/snmpsim-data/ `
  --license BSD-2-Clause
```

The inventory command reads files only to calculate their SHA-256 checksums.
It does not copy recordings or communicate with any SNMP agent.

Corpus measurement defaults to a 16 MiB decompressed limit per recording so a
single unusually large device cannot consume unbounded memory. Such evidence
is reported as `resource_limit`, not treated as incompatible or discarded.
Use `--max-recording-mib` to select a reviewed alternative budget.

TwinForge measures native `.snmprec`, compressed `.snmprec.bz2`, and common
numeric or MIB-symbolic Net-SNMP `.snmpwalk` output. Unrecognised walk lines
are counted and retained by the decoder rather than silently discarded. Other
file formats remain visible as `unsupported_format` results. SNMPSim
conversion remains available for unusual walk representations.

The simulator and client are deliberately separate adapters. SNMPSim provides
the agent; PySNMP will provide the manager/client used by TwinForge.

SNMPSim 1.2.2 currently needs `pysmi-lextudio` at runtime although it was not
installed by its published runtime dependencies in this environment. The full
responder also loads cryptographic SNMPv3 support during startup. Both are
declared explicitly in TwinForge's `snmp-sim` group. The lite responder is not
used because it calls a removed PySNMP dispatcher API.
