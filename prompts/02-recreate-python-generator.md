# Prompt: Recreate Python XSD-to-XML generator

Use with: Read `prompts/00-project-brief.md` first.

## Task

Implement **xsd2sample.py** (Python 3, standard library only) that:

1. **Accepts:** One argument: path to an XSD file. Optional `-o/--output <file>` and `--root <elementName>`.

2. **Parses XSD and includes:**
   - Parse the given XSD; for each `xs:include` with `schemaLocation`, load that file from the **same directory** as the current XSD and merge (same namespace).
   - Collect only **top-level** definitions: `xs:complexType`, `xs:simpleType`, `xs:group`, `xs:element` (direct children of `xs:schema`).

3. **Root element:**
   - Prefer the global element defined in the **main** XSD file (the one passed on the command line), not in an included file. If none, use the first global element.

4. **Generate XML:**
   - Resolve the root element’s `type` (support unqualified and prefixed type names).
   - For **complexType:** handle `xs:sequence`, `xs:choice`, `xs:all`; for each `xs:element` resolve its `type` or `ref`; for `xs:group ref="..."` expand the group; for `xs:attribute` emit attributes (use `default` or `fixed` if present, else e.g. `"sample"`).
   - For **simpleType:** use `xs:restriction` base to pick a sample (e.g. `xs:string` → `"sample"`, `xs:date` → `"2025-03-05"`).
   - Use element **default** / **fixed** from the schema when present.

5. **Output:**
   - Emit XML with correct `targetNamespace` on the root (use a prefix, e.g. `ncts:`); child elements follow `elementFormDefault` (unqualified = no prefix on children).
   - Write to the path given by `-o`, or print to stdout if `-o` is omitted.

Do **not** run validation inside the Python script; that is done by the shell script.
