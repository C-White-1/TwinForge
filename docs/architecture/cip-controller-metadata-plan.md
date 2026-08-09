# CIP Controller Metadata Plan

`CipControllerMetadataPlan` is a socket-free allowlist of object reads for one
controller. Every `CipControllerMetadataRequest` declares:

- a read-only CIP service;
- class, instance, and optional attribute numbers;
- whether the object is standard CIP or vendor-specific;
- its specification or fixture reference;
- an optional vendor-neutral semantic field and decoder; and
- a fixed one-request budget.

Only `Get_Attributes_All` and `Get_Attribute_Single` are permitted. A single
attribute is mandatory for the latter and prohibited for the former.
Vendor-specific reads require an explicit vendor ID; standard CIP reads reject
vendor attribution.

The serialized plan is a dry-run document containing the exact route, request
order, request keys, and total budget. It explicitly states that runtime values
are not permitted. Tag metadata and tag-value reads belong to separate Phase 4
operations and cannot be implied by controller metadata authorization.

This milestone does not select undocumented Rockwell object numbers or issue
requests. Vendor-specific examples remain labelled as pending authorized
fixtures until a specification or controlled-laboratory response supports
their semantics.
