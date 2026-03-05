# xsdthing

Generate valid sample XML from XSD schemas. The script follows `xs:include` (and resolves types from included files), picks the root element from the main schema, and produces XML that validates against the original XSD.

## Prerequisites

- **Python 3** (stdlib only; no `pip install` needed)
- **xmllint** (libxml2), for validation — e.g. `brew install libxml2` on macOS

## Quick start

```bash
./xsd2sample.sh DDNTA_APP/order.xsd
# Creates DDNTA_APP/order.xml and validates it.

./xsd2sample.sh DDNTA_APP/cc029.xsd
# Creates DDNTA_APP/cc029.xml (input basename + .xml).

./xsd2sample.sh DDNTA_APP/order.xsd custom.xml
# Writes to custom.xml (relative to cwd) and validates.
```

## Usage

| Command | Result |
|--------|--------|
| `./xsd2sample.sh <path/file.xsd>` | Output: `<path/file>.xml` (same folder as the XSD); then validate. |
| `./xsd2sample.sh <path/file.xsd> <out.xml>` | Output: `<out.xml>`; then validate. |

You can pass a path that includes a folder, e.g. `DDNTA_APP/order.xsd`. The script resolves the path so that `xs:include` (e.g. `ctypes.xsd`) are loaded from the XSD’s directory.

## Python script (optional)

You can call the generator directly:

```bash
python3 xsd2sample.py order.xsd -o order.xml
python3 xsd2sample.py order.xsd                    # print XML to stdout
python3 xsd2sample.py order.xsd --root CC004C -o out.xml
```

Options: `-o/--output` (output file), `--root` (root element name). Validation is not run when using the Python script alone; use the shell script for generate + validate.

## Schema layout (this repo)

XSDs live in **DDNTA_APP/**:

- **order.xsd** — Main schema; includes `ctypes.xsd` and `htypes.xsd`, defines root element (e.g. `CC004C`).
- **ctypes.xsd** — Common types (e.g. address, person, message group) and types used by the root (e.g. `TransitOperationType01`).
- **htypes.xsd** — Placeholder for extra shared types; can be extended.

Included schemas must use the same `targetNamespace` as the main schema (`xs:include`). The generator prefers the root element defined in the file you pass (e.g. `CC004C` from `order.xsd`, not `address` from `ctypes.xsd`).

## How it works

1. Parse the given XSD and any `xs:include`’d schemas from the same directory.
2. Collect global elements, complex/simple types, and groups; resolve type references (including prefixed names).
3. Choose the root element (from the main schema if possible) and recursively build a sample instance from its type (sequences, choices, attributes, defaults).
4. Emit XML with the correct target namespace on the root; child elements follow `elementFormDefault` (e.g. unqualified).
5. (Shell script only) Run `xmllint --schema` on the generated file and exit successfully only if validation passes.

## Limitations

- Only `xs:include` is followed (same namespace); `xs:import` is not resolved.
- One root element per run; no support for multiple documents or substitution groups.
- Sample values are generic (“sample”, “0”, a fixed date) unless the schema defines `default` or `fixed`; those are used when present.
