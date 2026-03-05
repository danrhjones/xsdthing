# Prompt: Recreate README

Use with: Read `prompts/00-project-brief.md` first.

## Task

Write **README.md** that is detailed but not too long. Include:

1. **Title and one-line description** — Generate valid sample XML from XSD; script follows includes, picks root from main schema, validates output.

2. **Prerequisites** — Python 3 (stdlib only), xmllint (libxml2); mention e.g. `brew install libxml2` on macOS.

3. **Quick start** — Three example commands using `DDNTA_APP/order.xsd` and `DDNTA_APP/cc029.xsd`; show default output naming and optional second argument for output path.

4. **Usage table** — Rows for: `./xsd2sample.sh <path/file.xsd>` → output `<path/file>.xml`; `./xsd2sample.sh <path/file.xsd> <out.xml>` → output to `<out.xml>`. Note that input can be folder + file.

5. **Python script (optional)** — How to run `xsd2sample.py` directly with `-o` and `--root`; note that validation is not run by the Python script alone.

6. **Schema layout** — XSDs live in `DDNTA_APP/`: order.xsd (main), ctypes.xsd, htypes.xsd; same targetNamespace for includes; root preferred from main file.

7. **How it works** — Short numbered list: parse + include, collect types/groups/elements, choose root, generate from type tree, (shell) validate with xmllint.

8. **Limitations** — xs:include only (no xs:import); single root; generic sample values unless default/fixed in schema.

Keep to about one page; no lengthy API docs.
