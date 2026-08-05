# SNMPSim Data Compatibility Experiment

## Purpose

Measure TwinForge's offline SNMP evidence ingestion against the published
`snmpsim-data` collection without committing third-party recordings or
contacting live SNMP agents.

## Source and provenance

- Source: <https://docs.lextudio.com/snmpsim-data/>
- Declared licence: BSD-2-Clause
- Recordings inventoried: 116
- Compressed source size: approximately 67.9 MB
- Decompressed `.snmprec` evidence: approximately 1.4 GB
- Corpus files committed to TwinForge: none

Each temporary recording was described by a manifest containing its relative
path, source URL, licence, device category, sanitisation declaration and
SHA-256 checksum.

## Method

TwinForge decoded `.snmprec` and `.snmprec.bz2` files locally, lowered their
canonical OID values through the same SNMP evidence path used by the synthetic
fixture, and applied a 16 MiB decompressed limit to each recording. Files over
the limit were reported as `resource_limit`; they were not classified as
incompatible.

Older recordings containing arbitrary non-UTF-8 octets are decoded with a
lossless Latin-1 fallback. This maps every source byte to a character and
avoids replacement or evidence loss.

## Initial finding

The first bounded pass demonstrated that the public corpus is large and
diverse enough to be a useful compatibility benchmark. Most recordings could
be measured within the default budget. Large router, wireless-controller and
network-appliance recordings account for the resource-limited cases.

| Result | Recordings |
| --- | ---: |
| Measured | 99 |
| Resource limit | 17 |
| Parse failures | 0 |

The 99 measured recordings yielded:

- 2,402,484 canonical OID records;
- 556 populated system fields;
- 2,526 interfaces;
- 1,092 interface addresses;
- 49 neighbour observations; and
- 1,276 forwarding-database entries.

Four malformed physical lines were retained from one legacy switch recording.
All other physical records within the measured set decoded successfully.
Consequently, this result means 99 recordings were compatible within the
default resource budget; it does not claim the 17 larger recordings are
incompatible.

## OID-family coverage

The measured evidence divides into three broad groups:

| Coverage group | OIDs | Approximate share |
| --- | ---: | ---: |
| Currently lowered standard families | 397,040 | 16.5% |
| Enterprise-specific evidence | 1,634,336 | 68.0% |
| Other standard or unclassified evidence | 371,108 | 15.4% |

This distinction is important: TwinForge preserves all canonical OIDs, but
does not claim that retained evidence has been semantically interpreted.
Enterprise branches remain named by Private Enterprise Number until an
authoritative registry or vendor specification supplies identity and meaning.

Prominent standard evidence-only families include:

| Family | OIDs | Potential TwinForge use |
| --- | ---: | --- |
| RMON-MIB | 71,868 | Ethernet statistics and monitoring evidence |
| HOST-RESOURCES-MIB | 61,858 | Host hardware, storage and software inventory |
| ENTITY-MIB (RFC 6933) | 32,069 | Physical inventory and containment |
| TCP-MIB | 26,770 | Transport endpoint evidence |
| OSPF-MIB | 25,582 | Routed topology evidence |

ENTITY-MIB is the strongest next semantic-lowering candidate for TwinForge's
asset-inventory goals. RMON has more observations, but primarily contributes
statistics rather than physical identity and containment. OSPF should remain
an explicit later topology phase rather than being inferred from generic IP
evidence.

The normative ENTITY-MIB reference is
[RFC 6933](https://www.rfc-editor.org/info/rfc6933/), version 4. It obsoletes
RFC 4133 while retaining the `mib-2.47` subtree. Any future TwinForge schema
and lowering implementation must follow RFC 6933, including its
`entPhysicalUUID` addition and IANA-maintained physical-class convention.

The family names are grounded in the IANA SMI Numbers registry and the
applicable IETF MIB specifications; the classifier does not require local MIB
files to retain or categorize numeric evidence.

## RFC 6933 ENTITY-MIB result

After implementing ENTITY-MIB v4 lowering, the same bounded corpus yielded:

- 1,624 physical entities;
- 23 recordings containing physical-entity evidence;
- 26 containment findings across three recordings;
- 26 `missing_parent` findings; and
- no self-parent or containment-cycle findings.

The missing parents occurred in two Cisco Nexus recordings and one HPE
ProCurve recording. They indicate that a referenced parent row was absent from
the captured evidence; they do not establish that the original device had an
invalid ENTITY-MIB hierarchy. TwinForge retains the observed parent indices
and reports incompleteness rather than synthesizing physical entities.

Final evidence totals should be regenerated with the checked-in inventory and
measurement commands whenever parsing or lowering rules change. The corpus
itself remains an external dependency rather than a repository fixture.
