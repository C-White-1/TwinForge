# CODESYS PLCopen XML import rules

Rules for writing PLCopen XML that CODESYS imports correctly. Each one was
found by importing TwinForge output into CODESYS V3.5 SP22 Patch 3 and
comparing it with CODESYS's own export of the same thing. The details are in
[the CODESYS runs](../experiments/codesys-library-compile.md).

**Read this before changing anything TwinForge writes for CODESYS.** Valid
TC6 XML is not enough: several of these documents passed the TC6 schema and
TwinForge's own tests, and CODESYS still rejected them. When CODESYS
rejects something new, **export the hand-built equivalent from CODESYS and
copy its form**, rather than guessing, then add the rule here.

## Names

### R and S are reserved words

- **Rule:** never name a parameter or variable `R` or `S`.
- **Why:** they are Instruction List operators, and ST's `S=`/`R=`
  set/reset assignments make them reserved in CODESYS. CODESYS underlines
  them in a declaration, and every call that uses them fails to parse
  (501 errors, "';' expected instead of ','").
- **In TwinForge:** Basic's `R`/`S` pins are exported as `RESET`/`LOAD`
  (counter) and `RESET`/`STEP_NO` (drum), mapped from the source pins by
  `GeneratedFunctionBlock.source_pins`. `STEP` is also reserved: it is an
  IEC SFC keyword.
- **Guard:** `test_generated_block_names_avoid_reserved_words`.

### Program names must be IEC identifiers

- **Rule:** never export a program name containing a space or another
  non-identifier character.
- **Why:** Machine Expert – Basic's default program is `New POU`. CODESYS
  cannot match `PROGRAM New POU` to its object ("The name used in the
  signature is not identical to the object name").
- **In TwinForge:** exported as `New_POU` everywhere the name is used, with a
  `program_name_rewritten` diagnostic.

## Text

### XHTML: declare the namespace on each element

- **Rule:** write `<xhtml xmlns="http://www.w3.org/1999/xhtml">`, not a prefix
  declared on the root (`<html:xhtml>`).
- **Why:** both are the same XML, but CODESYS's import silently dropped every
  variable `documentation` written with the prefix. The comments simply did
  not appear, with no error.
- **In TwinForge:** `xhtml_namespace_on_element` rewrites all PLCopen output.

## Ladder boxes

### Mark every unused output pin with an empty expression

- **Rule:** an output pin that nothing in the rung connects to is written
  with an empty `<expression/>` inside its `connectionPointOut`, as CODESYS
  exports an unused pin (its empty variable field).
- **Why:** CODESYS reads a bare `connectionPointOut` as one more output
  carrying the rung. With a second one (the drum's `F` wired to a coil and
  `STEP_NO` left bare), the import reports **"Block has too many outputs"**.
  The drum's 16 in-out pins caused the same error before.
- **In TwinForge:** `PLCopenExporter._mark_unconnected_outputs`, for the
  CODESYS profile.

### Contacts can drive several inputs

- **Rule:** a contact may feed any input pin of a box, not only the first
  one or `EN`.
- **Why:** observed. A hand-built box accepted contacts on both `EN` and `U`.

### Pins cannot be hidden or collapsed

- **Rule:** to keep a box small, move configuration off the pins. Do not
  rely on attributes.
- **Why:** `{attribute 'pingroup'}` showed no collapse control on a ladder
  box, and `{attribute 'hide'}` does not hide pins.
- **In TwinForge:** the drum takes its configuration through `FB_init`
  (below).

## Function blocks configured in their declaration

### FB_init parameters

- **Rule:** an instance is configured in its declaration,
  `D : Block(NAME := value, ...)`. TwinForge writes this as
  `inputassignments` on the instance variable, and the block's `FB_init`
  method as `method` data on its POU, both in CODESYS's own form.
- **Constraint:** an array argument must be a **variable**. An array literal
  is refused: "An array initialisation is not possible as parameter of an
  initial function call. Use a variable instead".
- **References:** `REFERENCE TO BOOL` parameters, stored with `REF=` and
  checked with `__ISVALIDREF`, write through correctly, and survive an
  online change.
- **Element order:** a POU may have only one `addData`, so its `method` and
  `objectid` data share it, and `documentation` comes after it.

### Declare what FB_init reads before the instance

- **Rule:** in a variable list, declare every variable an instance's
  `FB_init` arguments name (its pattern table, the outputs it references)
  **above** the instance.
- **Why:** CODESYS initialises a list in declaration order and runs FB_init
  as the instance's declaration is reached. With the table declared below,
  the build fails: "C0268: The uninitialized variable TF_DR0_Pattern is used
  for initialization of TF_DR0. Use the attribute 'global_init_slot' to
  change the order of initialisation". References to later variables give
  warnings (C0564).
- **In TwinForge:** `PLCopenExporter._initialisation_order`.

### CODESYS's export forms

All are `addData` under `http://www.3s-software.com/plcopenxml/`:

| What | Written as |
| --- | --- |
| Instance `FB_init` arguments | `inputassignments`: `<InputAssignment><Name>`, `<Value>` |
| `FB_init` method | `method`: `<Method name="FB_init" ObjectId>` with its own interface (return type, inputs) and ST body; an entry under the block in the project structure |
| Reference type | `<derived name="REFERENCE TO BOOL" />` |
| Attribute | `attributes`: `<Attribute Name Value>` |
| Installed library | `libraries`: `<Library Name="TwinForge_MEBasic, 0.3.0 (TwinForge)" Namespace="TwinForge_MEBasic" .../>`, after placeholder entries, before the placeholder redirections; instance types stay unqualified |

## Project and import behaviour

### Global variable lists are qualified_only

- **Rule:** use `List.Variable` (for example `TF_DrumPatterns.DR0_PATTERN`).
- **Why:** CODESYS creates a new global variable list with
  `{attribute 'qualified_only'}`, also when a script creates it. Unqualified
  names do not resolve.

### Importing an application duplicates it

- **Behaviour:** importing a CODESYS-profile export into a new project
  creates a second Application beside the template's.
- **Workaround:** delete the template's Application before importing. A
  cleaner import is still open.

### System event bindings are not exported or imported

- **Behaviour:** Task Configuration → System Events (for example
  `PrepareStart` → a handler function) is not in PLCopen XML. The export
  dialog has no Task Configuration entry; the handler functions and their
  libraries (`CmpApp` and others) are exported, the binding is not, and
  after an import the System Events tab is empty.
- **Consequence:** an exported handler is never called until it is bound.
  TwinForge must say so with a diagnostic.
- **Restoring it:** the native export of the Task Configuration does hold
  the binding (`alSysEventList`). A script can add the entry and import it
  back, but must **remove** the Task Configuration first: importing over it
  replaces only its tasks. An empty list is written `<Null Name="alSysEventList" />`.
- **Evidence:** [first-cycle run](../experiments/codesys-first-cycle.md).

### The library Overview page needs a licensed add-on

- **Behaviour:** a library's Overview page in the Library Manager stays
  blank unless it was built with CODESYS's licensed Library Documentation
  Support add-on.
- **Not the cause:** the `DocFormat` property, and saving as a compiled
  library. Block and parameter comments do show.
- **In TwinForge:** the overview lives in a README instead.
