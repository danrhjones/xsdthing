#!/usr/bin/env python3
"""
Generate a sample XML instance from an XSD schema.
Handles xs:include (same directory), complex/simple types, groups, and defaults.
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

XS = "http://www.w3.org/2001/XMLSchema"


def get_tag(elem, default=None):
    if elem is None:
        return default
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


def get_text(elem, default=""):
    if elem is None:
        return default
    return (elem.text or "").strip() or default


def parse_schema(path: Path, base_dir: Path, types: dict, groups: dict, elements: dict, target_ns: dict):
    """Parse an XSD file and merge types, groups, elements. Resolve includes."""
    tree = ET.parse(path)
    root = tree.getroot()

    # Resolve targetNamespace from root (may have default ns)
    ns = root.get("targetNamespace") or ""
    if path not in target_ns:
        target_ns[path] = ns

    # Handle includes first (same namespace)
    for inc in root.findall(f".//{{{XS}}}include"):
        loc = inc.get("schemaLocation")
        if not loc:
            continue
        included = base_dir / loc
        if included.exists() and included not in target_ns:
            parse_schema(included, base_dir, types, groups, elements, target_ns)

    # Register complexTypes (top-level)
    for ct in root:
        if get_tag(ct) == "complexType" and ct.get("name"):
            types[ct.get("name")] = (ct, ns, path)

    # Register simpleTypes (top-level)
    for st in root:
        if get_tag(st) == "simpleType" and st.get("name"):
            types[st.get("name")] = (st, ns, path)

    # Register groups (top-level)
    for gr in root:
        if get_tag(gr) == "group" and gr.get("name"):
            groups[gr.get("name")] = (gr, ns, path)

    # Register global elements (top-level xs:element only)
    for el in root:
        if get_tag(el) == "element" and el.get("name"):
            name = el.get("name")
            elements[name] = (el, ns, path)


def resolve_type_ref(type_ref: str, ns_map: dict, types: dict) -> tuple:
    """Resolve 'TypeName' or 'prefix:TypeName' to (elem, ns)."""
    if ":" in type_ref:
        _prefix, name = type_ref.split(":", 1)
        # Find type in types; match by name (could be in any loaded ns for include)
        for tname, (elem, ns, _) in types.items():
            if tname == name:
                return (elem, ns)
        return (None, None)
    else:
        for tname, (elem, ns, _) in types.items():
            if tname == type_ref:
                return (elem, ns)
        return (None, None)


def simple_type_sample(st_elem) -> str:
    """Return a sample value for a simpleType (restriction base)."""
    base = None
    for r in st_elem.findall(f".//{{{XS}}}restriction"):
        base = r.get("base")
        if base:
            break
    if not base:
        return "sample"
    base = base.split("}")[-1] if "}" in base else base
    samples = {
        "string": "sample",
        "normalizedString": "sample",
        "token": "sample",
        "integer": "0",
        "int": "0",
        "long": "0",
        "decimal": "0.00",
        "float": "0.0",
        "double": "0.0",
        "boolean": "false",
        "date": "2025-03-05",
        "dateTime": "2025-03-05T12:00:00",
        "time": "12:00:00",
        "positiveInteger": "1",
        "nonNegativeInteger": "0",
    }
    return samples.get(base, "sample")


def generate_for_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level=0):
    """Generate XML content for a type. Returns list of (tag, content_or_children, attrs, use_prefix)."""
    if type_elem is None:
        return []
    tag = get_tag(type_elem)
    if tag == "complexType":
        return generate_complex_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level)
    if tag == "simpleType":
        return [("__text__", simple_type_sample(type_elem), {}, False)]
    return []


def generate_complex_type(ct_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level):
    out = []
    # attributes (direct children of complexType)
    for attr in ct_elem.findall(f"{{{XS}}}attribute"):
        aname = attr.get("name")
        if not aname:
            continue
        default = attr.get("default") or attr.get("fixed")
        out.append(("__attr__", aname, default or "sample"))
    # content: sequence, choice, all, group
    for container in ct_elem:
        ctag = get_tag(container)
        if ctag == "sequence":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level))
        elif ctag == "all":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level))
        elif ctag == "choice":
            # pick first option
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level))
                break
    return out


def process_particle(particle, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level):
    tag = get_tag(particle)
    min_occurs = int(particle.get("minOccurs", 1))
    if min_occurs == 0 and tag == "element":
        # optional: still emit once for sample
        pass
    if tag == "element":
        name = particle.get("name")
        ref = particle.get("ref")
        if ref:
            if ":" in ref:
                name = ref.split(":")[-1]
            else:
                name = ref
            if name in elements:
                el_elem, el_ns, _ = elements[name]
                type_ref = el_elem.get("type")
                if type_ref:
                    type_elem, _ = resolve_type_ref(type_ref, {}, types)
                    if type_elem:
                        inner = generate_for_type(type_elem, el_ns or type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level + 1)
                        return [(name, inner, {}, element_form_qualified)]
        if name:
            type_ref = particle.get("type")
            default = particle.get("default") or particle.get("fixed")
            if type_ref:
                type_elem, _ = resolve_type_ref(type_ref, {}, types)
                if type_elem:
                    inner = generate_for_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level + 1)
                else:
                    inner = [("__text__", default or "sample", {}, False)]
            else:
                inner = [("__text__", default or "sample", {}, False)]
            return [(name, inner, {}, element_form_qualified)]
    if tag == "group":
        ref = particle.get("ref")
        if ref and ":" in ref:
            ref = ref.split(":")[-1]
        if ref and ref in groups:
            gr_elem, gr_ns, _ = groups[ref]
            result = []
            for seq in gr_elem.findall(f".//{{{XS}}}sequence"):
                for item in seq:
                    result.extend(process_particle(item, types, groups, elements, gr_ns or type_ns, target_ns, element_form_qualified, indent_level + 1))
            for ch in gr_elem.findall(f".//{{{XS}}}choice"):
                for item in ch:
                    result.extend(process_particle(item, types, groups, elements, gr_ns or type_ns, target_ns, element_form_qualified, indent_level + 1))
                    break
            return result
    return []


def serialize(node, ns_uri, prefix, qualified, indent=0):
    """Node is (name, content_list, attrs_dict, use_prefix). content_list items are (name, content, attrs, q) or ('__text__', value, {}, _) or ('__attr__', aname, value)."""
    if node[0] == "__text__":
        return str(node[1])
    if node[0] == "__attr__":
        return None  # handled at element level
    name, content_list, attrs, use_prefix = node[0], node[1], node[2] if len(node) > 2 else {}, node[3] if len(node) > 3 else False
    attr_parts = []
    child_parts = []
    text_parts = []
    for c in content_list:
        if isinstance(c, tuple):
            if c[0] == "__attr__":
                attr_parts.append(f' {c[1]}="{c[2]}"')
            elif c[0] == "__text__":
                text_parts.append(c[1])
            else:
                child_parts.append(serialize(c, ns_uri, prefix, qualified, indent + 1))
        else:
            child_parts.append(str(c))
    attrs_str = "".join(attr_parts)
    sp = "  " * indent
    if prefix and use_prefix and ns_uri:
        tag = f"{prefix}:{name}"
    else:
        tag = name
    if not child_parts and not text_parts:
        return f"{sp}<{tag}{attrs_str}/>"
    text = "".join(text_parts)
    if text and not child_parts:
        return f"{sp}<{tag}{attrs_str}>{text}</{tag}>"
    inner = "\n".join(ch for ch in child_parts if ch)
    return f"{sp}<{tag}{attrs_str}>\n{inner}\n{sp}</{tag}>"


def build_tree(root_name, root_content, ns_uri, prefix, element_form_qualified):
    """Build root element node; content may include __attr__ tuples."""
    return (root_name, root_content, {}, element_form_qualified)


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

    # Prefer root element from the main schema file
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

    # Default: element form unqualified (common for NCTS-style)
    ns_uri = el_ns or target_ns.get(xsd_path, "")
    element_form_qualified = False
    for path, ns in target_ns.items():
        if ns == ns_uri:
            break
    # Check first schema's elementFormDefault
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
