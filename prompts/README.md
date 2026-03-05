# Prompts for xsdthing

These prompts can be saved and reused (e.g. in Cursor, or as reference) to recreate or extend the xsdthing project.

## How to use

1. **Start with** `00-project-brief.md` — read it (or paste into the AI) as the main context for the project.
2. Use the numbered prompts as needed:
   - **01** — Recreate or fix the sample XSDs (ctypes, htypes, order with include).
   - **02** — Recreate or extend the Python generator (xsd2sample.py).
   - **03** — Recreate or change the bash wrapper (xsd2sample.sh).
   - **04** — Recreate or update the README.
   - **05** — Move XSDs to a folder (e.g. DDNTA_APP) and ensure folder+file input works.

You can run prompts in order to rebuild the project from scratch, or use a single prompt to change one part (e.g. only the README or only the bash script).

## File list

| File | Purpose |
|------|--------|
| `00-project-brief.md` | Project goal, constraints, what exists, conventions |
| `01-recreate-sample-xsds.md` | Sample XSDs with xs:include and default sample data |
| `02-recreate-python-generator.md` | xsd2sample.py behaviour and requirements |
| `03-recreate-bash-script.md` | xsd2sample.sh usage, paths, validation |
| `04-recreate-readme.md` | README structure and content |
| `05-folder-layout-and-testing.md` | DDNTA_APP layout, folder+file input, tests |
