# xsd2sample.py – analysis and refactor

## Can it be moved into other files?

**Yes.** The script is now split into a small package:

| Module | Responsibility |
|--------|----------------|
| **xsdthing/schema.py** | XSD parsing, includes, type/group/element registration, `resolve_type_ref`, `get_tag`, `get_text` |
| **xsdthing/simple_values.py** | Sample values for simple types: enumerations, pattern/length/fractionDigits handling, `BASE_SAMPLES`, `_fallback_sample` |
| **xsdthing/generate.py** | Content tree generation: `generate_for_type`, `generate_complex_type`, `process_particle` |
| **xsdthing/serialize.py** | Tree → XML string: `serialize`, `build_tree` |
| **xsd2sample.py** | CLI, argument parsing, and orchestration only |

The entry point remains `python3 xsd2sample.py` (or `./xsd2sample.sh`); it imports from `xsdthing`.

---

## Rule clean-up and duplicates

### Duplicates removed

1. **Duplicate dict key**  
   `NumericWithZero_8` was listed twice in the samples dict; the second overwrote the first. Kept a single entry in `BASE_SAMPLES` in `simple_values.py`.

2. **Three ways to get "GB" for two letters**  
   - `length_val == "2"` and `[A-Z]` or `[A-Za-z]` in pattern (inside loop)  
   - `pattern_val == "[A-Za-z]{2}"` (inside loop)  
   - `length_val == "2"` and `any(("[A-Z]" in p...) or "[A-Za-z]" in p...) for p in pattern_elems)` (after loop)  
   Consolidated to: one condition in the loop that handles both `pv == "[A-Za-z]{2}"` and `length_val == "2"` with `[A-Z]`/`[A-Za-z]` in `pv`, plus the single post-loop check for “length 2 and any pattern with letters” (for types that only have length and no literal `[A-Za-z]{2}`).

3. **[A-Z]* and [A-Z0-9]***  
   Both returned `"A"`. Replaced with one check: `pv in ("[A-Z]*", "[A-Z0-9]*")`.

### Structure clean-up

- **Four pattern loops → one loop + one MRN pre-scan**  
  Previously there were four separate `for pattern_elem in pattern_elems` loops. They are now:
  - One **pre-scan** over `pattern_elems`: if any pattern has NCTS-P5 or Transit MRN form, return the corresponding sample (so schema order of patterns does not force the legacy MRN).
  - One **main loop** over `pattern_elems` for all other pattern-based rules (email, currency, digits, fixed length, etc.).

- **`BASE_SAMPLES`**  
  The big “type name → sample” dict is in `simple_values.py` as `BASE_SAMPLES` and is used only in `_fallback_sample`. Adding or changing known types is in one place.

- **Helper**  
  `_pattern_matches(pv, *substrings)` is used for “all of these substrings in pattern” (e.g. MRN, ENS) to avoid repeated `in pv` checks.

### Possible future clean-up

- **Data-driven pattern rules**  
  Pattern rules could be a list of `(predicate, value)` (e.g. `(lambda pv, lv, st: "@" in pv, "user@example.com")`) and one loop that runs them in order. That would make adding rules easier but would need care with `length_val`, `st_elem`, and `pattern_elems`.

- **BASE_SAMPLES in a separate file**  
  `BASE_SAMPLES` could live in a JSON or Python data file and be loaded at import if you want to edit samples without touching code.

---

## Summary

- Code is split into `xsdthing` (schema, simple_values, generate, serialize) and a thin `xsd2sample.py` CLI.
- Duplicate key and redundant “two letters” / “[A-Z]*” style rules are consolidated.
- Pattern handling is a single main loop plus one MRN pre-scan so that NCTS-P5/Transit are preferred over legacy when a type has multiple MRN patterns.

All 124 ddnta_new message schemas still validate after the refactor.
