# xsdthing — Project brief

Use this as the main context when working on this project.

## Goal

- **Input:** Path to an XSD file (e.g. `DDNTA_APP/order.xsd` or `DDNTA_APP/cc029.xsd`).
- **Output:** A sample XML instance that **validates** against that XSD.
- **Output naming:** If no second argument is given, output file is the same path with extension changed to `.xml` (e.g. `cc029.xsd` → `cc029.xml`).

## Constraints

- Use **Python 3 standard library only** (no pip install).
- Use **xmllint** (libxml2) for validation.
- Support **folder + file** input (e.g. `DDNTA_APP/order.xsd`); includes like `ctypes.xsd` must resolve from the XSD’s directory.

## What exists

1. **xsd2sample.py** — Python script that:
   - Parses the given XSD and follows `xs:include` (same directory).
   - Picks the root element from the **main** schema file (not from included schemas).
   - Generates sample XML from types (sequences, groups, attributes, defaults).
   - Writes XML with correct target namespace; children follow `elementFormDefault`.

2. **xsd2sample.sh** — Bash script that:
   - Accepts `<path/to/schema.xsd>` and optional `[output.xml]`.
   - Resolves XSD to absolute path, runs the Python generator, then runs `xmllint --noout --schema ...` and exits 0 only if validation passes.

3. **DDNTA_APP/** — Folder containing:
   - `order.xsd` (main schema, root e.g. CC004C), `ctypes.xsd`, `htypes.xsd` (included).

## Conventions

- Root element is the first global element in the **main** XSD file.
- Included schemas use the same `targetNamespace` (`xs:include` only; no `xs:import` in scope).
