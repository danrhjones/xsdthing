#!/usr/bin/env bash
#
# Generate sample XML instance(s) from XSD schema(s) and validate.
# Usage:
#   ./xsd2sample.sh <schema.xsd> [output.xml]              # single file
#   ./xsd2sample.sh <folder>                               # all .xsd in folder
#   ./xsd2sample.sh --json-payload <schema.xsd>            # emit compact JSON with embedded XML
#   ./xsd2sample.sh --json-payload <folder>                # emit one JSON per schema (one per line)
#
# Single file: if output.xml is omitted, writes <basename>.xml in the
# same directory as this script.
# Folder: processes every .xsd in the given directory; each output is
# <basename>.xml next to the script. Reports pass/fail per file.
#

set -e

usage() {
  echo "Usage:" >&2
  echo "  $0 <schema.xsd> [output.xml]" >&2
  echo "  $0 <folder>" >&2
  echo "  $0 --json-payload [--kafka-topic TOPIC] [--sender S] [--recipient R] <schema.xsd|folder>" >&2
  echo "" >&2
  echo "Options:" >&2
  echo "  --json-payload        Print a compact JSON object (one line) with an embedded, escaped, flattened XML payload." >&2
  echo "  --kafka-topic TOPIC   kafkaTopicName value (default: transit.transit)" >&2
  echo "  --sender S            messageSender value (default: test)" >&2
  echo "  --recipient R         messageRecipient value (default: test)" >&2
  echo "  -h, --help            Show this help" >&2
}

JSON_PAYLOAD=0
KAFKA_TOPIC_NAME="transit.transit"
MESSAGE_SENDER="test"
MESSAGE_RECIPIENT="test"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json-payload)
      JSON_PAYLOAD=1
      shift
      ;;
    --kafka-topic)
      KAFKA_TOPIC_NAME="${2:-}"
      if [[ -z "$KAFKA_TOPIC_NAME" ]]; then
        echo "Error: --kafka-topic requires a value" >&2
        usage
        exit 1
      fi
      shift 2
      ;;
    --sender)
      MESSAGE_SENDER="${2:-}"
      if [[ -z "$MESSAGE_SENDER" ]]; then
        echo "Error: --sender requires a value" >&2
        usage
        exit 1
      fi
      shift 2
      ;;
    --recipient)
      MESSAGE_RECIPIENT="${2:-}"
      if [[ -z "$MESSAGE_RECIPIENT" ]]; then
        echo "Error: --recipient requires a value" >&2
        usage
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "Error: Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 1 ]]; then
  usage
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
  local tmp_xml

  XSD_DIR="$(cd "$(dirname "$XSD")" && pwd)"
  XSD_ABS="${XSD_DIR}/$(basename "$XSD")"

  if [[ "$JSON_PAYLOAD" -eq 1 ]]; then
    # Generate to stdout so we can embed it into JSON.
    # We still validate via a temp file to preserve current behavior.
    tmp_xml="$(mktemp -t xsd2sample.XXXXXX.xml)"
    trap 'rm -f "$tmp_xml"' RETURN

    if ! python3 "$GENERATOR" "$XSD_ABS" -o "$tmp_xml"; then
      echo "Error: Failed to generate XML for $XSD_ABS" >&2
      return 1
    fi

    if ! xmllint --noout --schema "$XSD_ABS" "$tmp_xml"; then
      echo "Error: Generated XML did not validate for $XSD_ABS" >&2
      return 1
    fi

    # Wrap the validated XML as compact JSON with the required declaration and flattening.
    python3 - "$KAFKA_TOPIC_NAME" "$MESSAGE_SENDER" "$MESSAGE_RECIPIENT" <"$tmp_xml" <<'PY'
import json
import re
import sys
import uuid
from datetime import datetime
from xml.etree import ElementTree as ET

topic = sys.argv[1]
sender = sys.argv[2]
recipient = sys.argv[3]
xml_in = sys.stdin.read()

xml_decl = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'

# Strip any existing XML declaration.
xml_body = re.sub(r'^\s*<\?xml[^?]*\?>\s*', '', xml_in, flags=re.S).strip()

# Flatten: remove whitespace between tags (preserve whitespace inside text/attributes).
xml_flat = re.sub(r'>\s+<', '><', xml_body)

payload = xml_decl + xml_flat

try:
    root = ET.fromstring(xml_body)
    tag = root.tag
    if tag.startswith("{") and "}" in tag:
        message_type = tag.split("}", 1)[1]
    else:
        message_type = tag.split(":")[-1]
except Exception:
    message_type = ""

try:
    prep_dt = datetime.now().isoformat(timespec="milliseconds")
except Exception:
    prep_dt = "2026-02-03T08:27:20.123"

mid = str(uuid.uuid4())
cid = mid

out = {
    "payload": payload,
    "kafkaTopicName": topic,
    "messageType": message_type,
    "preparationDateAndTime": prep_dt,
    "messageSender": sender,
    "messageRecipient": recipient,
    "messageIdentification": mid,
    "correlationIdentifier": cid,
}

print(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
PY

    return 0
  fi

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
    base="$(basename "$xsd" .xsd)"
    # Skip support/library schemas that have no root element (cannot generate a single document)
    case "$base" in
      ctypes|doc|htypes|stypes|tcl) continue ;;
    esac
    ((count++)) || true
    if process_one "$xsd" ""; then
      ((pass++)) || true
    else
      ((fail++)) || true
    fi
    if [[ "$JSON_PAYLOAD" -ne 1 ]]; then
      echo "---"
    fi
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
