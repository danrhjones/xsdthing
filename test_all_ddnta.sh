#!/usr/bin/env bash
# Run xsd2sample.sh on each message schema in ddnta and report pass/fail.
set +e
cd "$(dirname "$0")"
for f in ddnta/CC*.xsd ddnta/CD*.xsd; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .xsd)
  out=$(./xsd2sample.sh "$f" 2>&1)
  if echo "$out" | grep -q "validates against the schema"; then
    echo "PASS $name"
  else
    echo "FAIL $name"
    echo "$out" | grep -E "validity error|Error:" | head -3
  fi
done
