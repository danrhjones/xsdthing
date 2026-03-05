#!/usr/bin/env bash
#
# Generate sample XML instance(s) from XSD schema(s) and validate.
# Usage:
#   ./xsd2sample.sh <schema.xsd> [output.xml]   # single file
#   ./xsd2sample.sh <folder>                    # all .xsd in folder
#
# Single file: if output.xml is omitted, writes <basename>.xml in the
# same directory as this script.
# Folder: processes every .xsd in the given directory; each output is
# <basename>.xml next to the script. Reports pass/fail per file.
#

set -e

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <schema.xsd> [output.xml]  OR  $0 <folder>" >&2
  echo "  Single file: generate one XML from the XSD and validate." >&2
  echo "  Folder: process every .xsd in the directory; output each to <basename>.xml next to this script." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
GENERATOR="${SCRIPT_DIR}/xsd2sample.py"

if [[ ! -f "$GENERATOR" ]]; then
  echo "Error: Generator script not found: $GENERATOR" >&2
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required but not found." >&2
  exit 1
fi

if ! command -v xmllint &>/dev/null; then
  echo "Error: xmllint is required for validation (install libxml2)." >&2
  exit 1
fi

process_one() {
  local XSD="$1"
  local OUTPUT="${2:-}"
  local XSD_DIR XSD_ABS BASE

  XSD_DIR="$(cd "$(dirname "$XSD")" && pwd)"
  XSD_ABS="${XSD_DIR}/$(basename "$XSD")"

  if [[ -z "$OUTPUT" ]]; then
    BASE="$(basename "$XSD" .xsd)"
    OUTPUT="${SCRIPT_DIR}/${BASE}.xml"
  fi

  echo "Generating sample XML from $XSD_ABS ..."
  if ! python3 "$GENERATOR" "$XSD_ABS" -o "$OUTPUT"; then
    echo "Error: Failed to generate $OUTPUT" >&2
    return 1
  fi

  echo "Validating $OUTPUT against $XSD_ABS ..."
  if xmllint --noout --schema "$XSD_ABS" "$OUTPUT"; then
    echo "OK: $OUTPUT validates against the schema."
    return 0
  else
    echo "Error: $OUTPUT did not validate." >&2
    return 1
  fi
}

ARG="$1"
OUTPUT_ARG="${2:-}"

if [[ -d "$ARG" ]]; then
  # Folder: process all .xsd files
  DIR="$(cd "$ARG" && pwd)"
  count=0
  pass=0
  fail=0
  for xsd in "$DIR"/*.xsd; do
    [[ -f "$xsd" ]] || continue
    ((count++)) || true
    if process_one "$xsd" ""; then
      ((pass++)) || true
    else
      ((fail++)) || true
    fi
    echo "---"
  done
  if [[ $count -eq 0 ]]; then
    echo "No .xsd files found in $DIR" >&2
    exit 1
  fi
  echo "Done: $pass passed, $fail failed (of $count schemas)."
  [[ $fail -eq 0 ]]
elif [[ -f "$ARG" ]]; then
  # Single file
  process_one "$ARG" "$OUTPUT_ARG"
else
  echo "Error: Not a file or directory: $ARG" >&2
  exit 1
fi
