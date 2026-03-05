#!/usr/bin/env bash
#
# Generate a sample XML instance from an XSD schema and validate it.
# Usage: ./xsd2sample.sh <schema.xsd> [output.xml]
#
# If output.xml is omitted, writes to <basename>.xml in the same
# directory as the XSD (e.g. cc029.xsd → cc029.xml) and validates.
#

set -e

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <schema.xsd> [output.xml]" >&2
  echo "  Generates a sample XML from the XSD and validates it." >&2
  exit 1
fi

XSD="$1"
OUTPUT="${2:-}"

if [[ ! -f "$XSD" ]]; then
  echo "Error: Schema file not found: $XSD" >&2
  exit 1
fi

# Resolve to absolute path so includes resolve from the schema's directory
XSD_DIR="$(cd "$(dirname "$XSD")" && pwd)"
XSD_ABS="${XSD_DIR}/$(basename "$XSD")"

if [[ -z "$OUTPUT" ]]; then
  BASE="$(basename "$XSD" .xsd)"
  OUTPUT="${XSD_DIR}/${BASE}.xml"
fi

# Script directory: find xsd2sample.py next to this script or in current dir
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

echo "Generating sample XML from $XSD_ABS ..."
python3 "$GENERATOR" "$XSD_ABS" -o "$OUTPUT"

echo "Validating $OUTPUT against $XSD_ABS ..."
if xmllint --noout --schema "$XSD_ABS" "$OUTPUT"; then
  echo "OK: $OUTPUT validates against the schema."
else
  echo "Error: Generated XML did not validate." >&2
  exit 1
fi
