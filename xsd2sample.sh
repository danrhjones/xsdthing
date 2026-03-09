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
  echo "  $0 --bruno [--bruno-dir DIR] <folder>           # write Bruno .bru files (POST + JSON body)" >&2
  echo "" >&2
  echo "Options:" >&2
  echo "  --json-payload        Print a compact JSON object (one line) with an embedded, escaped, flattened XML payload." >&2
  echo "  --bruno               For each message XSD, create a Bruno .bru file (POST, sample URL, JSON body)." >&2
  echo "  --bruno-dir DIR       Directory for .bru files (default: bruno). Use with --bruno." >&2
  echo "  --prefix PREFIX       Namespace prefix for targetNamespace (default: ncts)" >&2
  echo "  --kafka-topic TOPIC   kafkaTopicName value (default: transit.transit)" >&2
  echo "  --sender S            messageSender value (default: test)" >&2
  echo "  --recipient R         messageRecipient value (default: test)" >&2
  echo "  -h, --help            Show this help" >&2
}
 
JSON_PAYLOAD=0
BRUNO_DIR=""
NS_PREFIX="ncts"
KAFKA_TOPIC_NAME="transit.transit"
MESSAGE_SENDER="test"
MESSAGE_RECIPIENT="test"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json-payload)
      JSON_PAYLOAD=1
      shift
      ;;
    --bruno)
      BRUNO_DIR="bruno"
      shift
      ;;
    --bruno-dir)
      BRUNO_DIR="${2:-bruno}"
      if [[ -z "$BRUNO_DIR" ]]; then
        echo "Error: --bruno-dir requires a value" >&2
        usage
        exit 1
      fi
      shift 2
      ;;
    --prefix)
      NS_PREFIX="${2:-ncts}"
      shift 2
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

  # Bruno-only: create .bru files only when --bruno/--bruno-dir is set. No XML or JSON output.
  if [[ -n "$BRUNO_DIR" ]]; then
    tmp_xml="$(mktemp -t xsd2sample.XXXXXX.xml)"
    trap 'rm -f "$tmp_xml"' RETURN
    python3 "$GENERATOR" "$XSD_ABS" --prefix "$NS_PREFIX" -o "$tmp_xml" &>/dev/null || { echo "Error: Failed to generate XML for $XSD_ABS" >&2; return 1; }
    xmllint --noout --schema "$XSD_ABS" "$tmp_xml" &>/dev/null || true
    python3 - "$tmp_xml" "$KAFKA_TOPIC_NAME" "$MESSAGE_SENDER" "$MESSAGE_RECIPIENT" "$BRUNO_DIR" "$(basename "$XSD" .xsd)" <<'BRUPY'
import json, os, re, sys, uuid
from datetime import datetime
from xml.etree import ElementTree as ET
xml_path, topic, sender, recipient, bruno_dir, base_name = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
with open(xml_path, "r", encoding="utf-8") as f:
    xml_in = f.read()
xml_body = re.sub(r'^\s*<\?xml[^?]*\?>\s*', '', xml_in, flags=re.S).strip()
payload = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>' + re.sub(r'>\s+<', '><', xml_body)
try:
    root = ET.fromstring(xml_body)
    message_type = (root.tag.split("}", 1)[1] if "}" in root.tag else root.tag.split(":")[-1])
except Exception:
    message_type = ""
try:
    prep_dt = datetime.now().isoformat(timespec="milliseconds")
except Exception:
    prep_dt = "2026-02-03T08:27:20.123"
mid = str(uuid.uuid4())[:35]
out = {"payload": payload, "kafkaTopicName": topic, "messageType": message_type, "preparationDateAndTime": prep_dt, "messageSender": sender, "messageRecipient": recipient, "messageIdentification": mid, "correlationIdentifier": mid}
os.makedirs(bruno_dir, exist_ok=True)
js = json.dumps(out, indent=2, ensure_ascii=False)
indented = "\n".join("  " + line for line in js.splitlines())
for label, url_suffix in [("21", "iegb"), ("29", "iexi")]:
    name = f"api {label} {base_name}"
    path = os.path.join(bruno_dir, f"{name}.bru")
    url = f"https://example.com/transit/messages/{url_suffix}"
    with open(path, "w", encoding="utf-8") as f:
        f.write("meta {\n  name: " + name + "\n  type: http\n  seq: 1\n}\n\nhttp {\n  method: POST\n  url: " + url + "\n  headers: {\n    x-correlation-id: {{$randomUUID}}\n    x-conversation-id: {{$randomUUID}}\n    date: {{timestamp}}\n  }\n  body: json\n  auth: none\n}\n\nbody:json {\n" + indented + "\n}\n")
BRUPY
    return 0
  fi

  if [[ "$JSON_PAYLOAD" -eq 1 ]]; then
    # Generate to stdout so we can embed it into JSON.
    # We still validate via a temp file to preserve current behavior.
    tmp_xml="$(mktemp -t xsd2sample.XXXXXX.xml)"
    trap 'rm -f "$tmp_xml"' RETURN

    if ! python3 "$GENERATOR" "$XSD_ABS" --prefix "$NS_PREFIX" -o "$tmp_xml"; then
      echo "Error: Failed to generate XML for $XSD_ABS" >&2
      return 1
    fi

    if ! xmllint --noout --schema "$XSD_ABS" "$tmp_xml"; then
      echo "Error: Generated XML did not validate for $XSD_ABS" >&2
      return 1
    fi

    # Wrap the validated XML as compact JSON with the required declaration and flattening.
    # Pass temp file path as arg so we read XML from file (stdin is the heredoc script).
    # When BRUNO_DIR is set, pass it and base name; Python will write a .bru file instead of printing.
    python3 - "$tmp_xml" "$KAFKA_TOPIC_NAME" "$MESSAGE_SENDER" "$MESSAGE_RECIPIENT" ${BRUNO_DIR:+"$BRUNO_DIR" "$(basename "$XSD" .xsd)"} <<'PY'
import json
import os
import re
import sys
import uuid
from datetime import datetime
from xml.etree import ElementTree as ET

xml_path = sys.argv[1]
topic = sys.argv[2]
sender = sys.argv[3]
recipient = sys.argv[4]
bruno_dir = sys.argv[5] if len(sys.argv) >= 6 else None
base_name = sys.argv[6] if len(sys.argv) >= 7 else None

with open(xml_path, "r", encoding="utf-8") as f:
    xml_in = f.read()

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

mid = str(uuid.uuid4())[:35]
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

if bruno_dir and base_name:
    os.makedirs(bruno_dir, exist_ok=True)
    bru_path = os.path.join(bruno_dir, f"api - {base_name}.bru")
    json_str = json.dumps(out, indent=2, ensure_ascii=False)
    json_indented = "\n".join("  " + line for line in json_str.splitlines())
    bru_content = f"""meta {{
  name: api - {base_name}
  type: http
  seq: 1
}}

http {{
  method: POST
  url: https://example.com/transit/messages
  body: json
  auth: none
}}

body:json {{
{json_indented}
}}
"""
    with open(bru_path, "w", encoding="utf-8") as f:
        f.write(bru_content)
else:
    print(json.dumps(out, indent=2, ensure_ascii=False))
PY

    return 0
  fi

  if [[ -z "$OUTPUT" ]]; then
    BASE="$(basename "$XSD" .xsd)"
    OUTPUT="${SCRIPT_DIR}/${BASE}.xml"
  fi

  echo "Generating sample XML from $XSD_ABS ..."
  if ! python3 "$GENERATOR" "$XSD_ABS" --prefix "$NS_PREFIX" -o "$OUTPUT"; then
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
    if [[ "$JSON_PAYLOAD" -ne 1 ]] && [[ -z "$BRUNO_DIR" ]]; then
      echo "---"
    fi
    if [[ -n "$BRUNO_DIR" ]]; then
      echo "  api 21 $base.bru, api 29 $base.bru"
    fi
  done
  if [[ $count -eq 0 ]]; then
    echo "No .xsd files found in $DIR" >&2
    exit 1
  fi
  if [[ -n "$BRUNO_DIR" ]]; then
    echo "Done: $(( pass * 2 )) .bru files ($pass schemas) written to $BRUNO_DIR/"
  else
    echo "Done: $pass passed, $fail failed (of $count schemas)."
  fi
  [[ $fail -eq 0 ]]
elif [[ -f "$ARG" ]]; then
  # Single file
  process_one "$ARG" "$OUTPUT_ARG"
else
  echo "Error: Not a file or directory: $ARG" >&2
  exit 1
fi
