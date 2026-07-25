# AutomationML and CAEX references

TwinForge currently targets AutomationML 2.1 using CAEX 3.0 and the namespace:

```text
http://www.dke.de/CAEX
```

Development references were obtained from the official AutomationML site and
are stored locally under the ignored directory `reference/AutomationML/`:

- `WP AutomationML Edition 2.pdf`
- `AutomationML2.10BaseLibraries.aml`
- `CAEX_ClassModel_V.3.0.xsd`

The base-library filename uses `2.10` to represent version 2.1.0.

The `reference/` directory is excluded from version control. TwinForge does not
redistribute these files unless their redistribution terms are confirmed.
Users obtain them from:

- <https://www.automationml.org/about-automationml/specifications/>
- <https://www.automationml.org/about-automationml/publications/amlbook/a-practical-guide/chapter-2-the-caex-and-automationml-guide/>

Validation has two layers:

1. CAEX 3.0 XSD validation checks XML structure and ordering.
2. TwinForge semantic validation resolves class/type paths, external AML
   references, unique IDs, internal-link endpoints and PLCopen document
   references.

The generated AML references the official base library and defines separate
TwinForge role, interface, attribute-type and SystemUnitClass libraries.
Rockwell catalog SystemUnitClasses derive from vendor-neutral TwinForge
templates.
