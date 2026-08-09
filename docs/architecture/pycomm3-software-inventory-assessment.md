# pycomm3 Software Inventory Assessment

TwinForge inspected the locally installed `pycomm3 1.2.16` implementation
without connecting to a controller.

`LogixDriver.get_tag_list("*")` can expose controller and program tag
definitions. Its filtering logic also recognizes symbol records prefixed with
`Program:`, `Routine:` and `Task:`, allowing the library to assemble program,
routine and task metadata.

The public API is not currently compatible with
`PermittedSoftwareInventoryExecutor`. `get_tag_list` calls an internal upload
method that follows partial-transfer responses in its own loop. The caller
cannot authorize and count each page before the next transport request occurs.
Detecting the final number of requests would not satisfy TwinForge's preventive
budget boundary.

The versioned assessment therefore records all four capabilities as
discoverable but sets both `externally_budget_controllable` and
`live_executor_compatible` to `false`. Uninspected pycomm3 versions claim no
capabilities.

A live adapter requires one of the following:

- a public pycomm3 page-level API;
- an upstream request-budget or cancellation callback; or
- a separately tested low-level adapter backed by specification and packet
  fixtures.

TwinForge must not depend directly on pycomm3 private methods as though they
were a stable public interface.
