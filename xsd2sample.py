#!/usr/bin/env python3
"""
Generate a sample XML instance from an XSD schema.
Handles xs:include (same directory), complex/simple types, groups, and defaults.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from xsdthing import (
    parse_schema,
    resolve_type_ref,
    simple_type_sample,
    generate_for_type,
    serialize,
    build_tree,
)


def main():
    parser = argparse.ArgumentParser(description="Generate sample XML from XSD")
    parser.add_argument("xsd", type=Path, help="Path to the XSD file")
    parser.add_argument("-o", "--output", type=Path, help="Output XML file (default: stdout)")
    parser.add_argument("--root", type=str, help="Root element name (default: first global element)")
    args = parser.parse_args()

    xsd_path = args.xsd.resolve()
    if not xsd_path.exists():
        print(f"Error: XSD file not found: {xsd_path}", file=sys.stderr)
        sys.exit(1)
    base_dir = xsd_path.parent

    types = {}
    groups = {}
    elements = {}
    target_ns = {}
    parse_schema(xsd_path, base_dir, types, groups, elements, target_ns)

    if not elements:
        print("Error: No global elements found in schema.", file=sys.stderr)
        sys.exit(1)

    main_el_names = [name for name, (_, _, p) in elements.items() if p == xsd_path]
    if args.root:
        root_el_name = args.root
    elif main_el_names:
        root_el_name = main_el_names[0]
    else:
        root_el_name = list(elements.keys())[0]
    if root_el_name not in elements:
        print(f"Error: Root element '{root_el_name}' not found. Available: {list(elements.keys())}", file=sys.stderr)
        sys.exit(1)

    el_elem, el_ns, _ = elements[root_el_name]
    type_ref = el_elem.get("type")
    if not type_ref:
        print("Error: Root element has no type.", file=sys.stderr)
        sys.exit(1)

    type_elem, type_ns = resolve_type_ref(type_ref, {}, types)
    if not type_elem:
        print(f"Error: Type '{type_ref}' not found.", file=sys.stderr)
        sys.exit(1)

    ns_uri = el_ns or target_ns.get(xsd_path, "")
    tree = ET.parse(xsd_path)
    schema = tree.getroot()
    eq = schema.get("elementFormDefault", "unqualified")
    element_form_qualified = eq == "qualified"

    content = generate_for_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified)
    root_node = build_tree(root_el_name, content, ns_uri, "ncts" if ns_uri else None, True)
    body = serialize(root_node, ns_uri, "ncts" if ns_uri else None, True)

    decl = '<?xml version="1.0" encoding="UTF-8"?>\n'
    if ns_uri:
        body = body.replace(f"<ncts:{root_el_name}", f'<ncts:{root_el_name} xmlns:ncts="' + ns_uri + '"', 1)
    xml_out = decl + body + "\n"

    if args.output:
        args.output.write_text(xml_out, encoding="utf-8")
    else:
        print(xml_out)


if __name__ == "__main__":
    main()
