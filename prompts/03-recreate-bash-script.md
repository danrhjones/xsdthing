# Prompt: Recreate bash wrapper script

Use with: Read `prompts/00-project-brief.md` first.

## Task

Implement **xsd2sample.sh** (executable bash script) that:

1. **Usage:** `./xsd2sample.sh <schema.xsd> [output.xml]`
   - First argument: path to XSD (may include a folder, e.g. `DDNTA_APP/order.xsd`).
   - Second argument: optional output path. If omitted, output is **same directory as the XSD**, filename = basename of XSD with extension `.xml` (e.g. `cc029.xsd` → `cc029.xml`).

2. **Resolve paths:**
   - Convert XSD path to **absolute** (using `dirname`/`basename` and `cd ... && pwd`) so that the Python generator and xmllint see the same path and includes resolve from the XSD’s directory.

3. **Find generator:**
   - Look for `xsd2sample.py` in the **same directory as the script** (`SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"`).

4. **Prerequisites:**
   - Check `python3` and `xmllint` are available; exit with a clear error if not.

5. **Run:**
   - Run: `python3 "$GENERATOR" "$XSD_ABS" -o "$OUTPUT"`.
   - Then: `xmllint --noout --schema "$XSD_ABS" "$OUTPUT"`.
   - Exit **0** only if both succeed; on validation failure, print an error and exit **1**.

Use `set -e`. Print short progress messages (e.g. "Generating sample XML from ...", "Validating ...", "OK: ... validates against the schema.").
