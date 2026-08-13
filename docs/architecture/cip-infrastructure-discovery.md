# CIP infrastructure discovery

TwinForge treats CIP Assembly Object and Connection Manager Object discovery as
bounded evidence capture. It does not scan arbitrary instances or infer cyclic
I/O layouts from common device conventions.

## Planning boundary

`CipInfrastructureDiscoveryPlan` describes a socket-free allowlist. Every plan
identifies:

- the authorized target and engagement;
- an authorization reference;
- each exact object, instance, service, and optional attribute;
- the specification or device-profile source for that request; and
- a maximum request budget covering the complete allowlist.

Only the standard CIP Assembly Object class `0x04` and Connection Manager
Object class `0x06` are admitted. The current services are read-only
`Get_Attributes_All` and `Get_Attribute_Single`.

## Evidence requirements

Assembly instance numbers and meanings must come from evidence such as an EDS,
a vendor device profile, an approved configuration export, or an applicable
specification. A familiar input/output assembly number is not enough evidence
to assign a semantic meaning.

Connection Manager reads likewise require an exact, cited instance and
attribute. A successful response proves only that the requested object evidence
was returned at capture time. It does not prove that an I/O connection is
configured, established, healthy, or owned by a particular controller.

## Deliberate exclusions

The planning milestone does not:

- open a network socket;
- enumerate unspecified instance ranges;
- establish or close a CIP connection;
- use `Forward_Open`, `Large_Forward_Open`, or `Unconnected_Send`;
- read application tag values; or
- decode payload fields without a cited profile.

`PermittedCipInfrastructureExecutor` applies the existing routed
execution-permit pattern. It preflights the authorization reference and exact
route before transport I/O, executes each allowlisted request once, and then
exhausts the plan budget.

Every result is preserved as `CipObjectEvidence`, including:

- general and additional status words;
- the response payload as hexadecimal text;
- the raw reply when supplied by the transport; and
- any transport-provided diagnostic message.

Successful and failed reads follow the same evidence path. Semantic decoding
remains a separate profile-driven stage so unknown bytes and status words stay
unchanged.

## Profile-driven decoding

`CipInfrastructureDecodeProfile` must match the planned class, instance,
attribute, and service exactly. Each decoded field declares its byte offset,
width, primitive representation, byte order, and specification reference.
Profiles reject duplicate names, overlapping fields, invalid widths, and
payload-size conflicts.

Only successful responses are decoded. The original response payload remains
unchanged and bytes not claimed by the profile are retained as
`unclaimed_payload_hex`.

An EDS assembly reference such as `Assem1` is not assumed to identify CIP
instance number 1. Connection paths and endpoint declarations remain source
evidence, but a field layout requires a separate exact profile supported by the
EDS, device manual, applicable specification, or approved configuration
evidence.
