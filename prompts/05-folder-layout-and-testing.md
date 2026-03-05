# Prompt: Folder layout and folder+file input

Use with: Read `prompts/00-project-brief.md` first.

## Task

1. **Move XSDs into a subfolder**
   - Create a folder (e.g. **DDNTA_APP**).
   - Move all XSD files used by the project into that folder (e.g. `order.xsd`, `ctypes.xsd`, `htypes.xsd`).
   - Do **not** change the content of the XSDs; only their location. Ensure `xs:include schemaLocation="ctypes.xsd"` etc. still work (relative to the same folder).

2. **Support folder + file input**
   - The script must accept a path that includes a folder, e.g. `DDNTA_APP/order.xsd` or `DDNTA_APP/cc029.xsd`.
   - Default output when given `DDNTA_APP/order.xsd` must be **DDNTA_APP/order.xml** (same directory as the XSD).
   - No script logic change should be required if the script already uses `dirname`/`basename` and resolves the XSD to an absolute path; just verify and test.

3. **Test**
   - Run: `./xsd2sample.sh DDNTA_APP/order.xsd`
   - Confirm: `DDNTA_APP/order.xml` is created and `xmllint` reports that it validates.
   - Optionally run with an explicit output path: `./xsd2sample.sh DDNTA_APP/order.xsd other.xml` and confirm `other.xml` validates.

4. **Update README**
   - Update README examples to use `DDNTA_APP/order.xsd` and `DDNTA_APP/cc029.xsd`.
   - Document that the input can be a path with a folder and that output is written next to the XSD by default.
