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


def simple_type_sample(st_elem, types: dict) -> str:
    """Return a sample value for a simpleType (enumeration first, then restriction base/pattern/length)."""
    if st_elem is None:
        return "sample"
    # Prefer first xs:enumeration value if present
    for enum in st_elem.findall(f".//{{{XS}}}enumeration"):
        val = enum.get("value")
        if val is not None:
            return val
    # Resolve restriction base and facets
    base = None
    restriction = None
    for r in st_elem.findall(f".//{{{XS}}}restriction"):
        base = r.get("base")
        if base:
            restriction = r
            break
    if not base:
        return "sample"
    base_local = base.split("}")[-1] if "}" in base else base

    # Check length/maxLength/pattern facets for common cases (before base lookup)
    if restriction is not None:
        length_elem = restriction.find(f"{{{XS}}}length")
        max_length_elem = restriction.find(f"{{{XS}}}maxLength")
        pattern_elems = restriction.findall(f"{{{XS}}}pattern")
        length_val = length_elem.get("value") if length_elem is not None else None
        max_length_val = max_length_elem.get("value") if max_length_elem is not None else None

        # Pattern-based samples first (before maxLength, so email etc. get correct value)
        for pattern_elem in pattern_elems:
            pattern_val = pattern_elem.get("value") or ""
            # Email pattern (e.g. \P{Z}[^@]*@[^\.]+\..*\P{Z})
            if "@" in pattern_val:
                return "user@example.com"
            # MRN NCTS-P5 (prefer over legacy when type has both patterns)
            if "[J-M][0-9]" in pattern_val and "[A-Z0-9]{12}" in pattern_val:
                return "24GB123456789012K1"
        # Second pass: legacy MRN and GRN (only if NCTS-P5 not chosen)
        for pattern_elem in pattern_elems:
            pattern_val = pattern_elem.get("value") or ""
            if "[A-Z0-9]{13}[0-9]" in pattern_val:
                return "24AB1234567890123"
            if "[0-9]{2}[A-Z]{2}[A-Z0-9]{12}[0-9]" in pattern_val:
                return "24GB1234567890123"
        for pattern_elem in pattern_elems:
            pattern_val = pattern_elem.get("value") or ""
            # [A-Z]{2}[!-~]{1,15} (identificationNumber)
            if "[A-Z]{2}[!-~]" in pattern_val:
                return "GB12345678901"
            # [A-Za-z]{3} (currency)
            if pattern_val.strip() == "[A-Za-z]{3}" or (length_val == "3" and "[A-Za-z]" in pattern_val):
                return "EUR"
            # [A-Za-z]{2}
            if length_val == "2" and ("[A-Z]" in pattern_val or "[A-Za-z]" in pattern_val):
                return "GB"
            # [A-Za-z]{1}
            if pattern_val == "[A-Za-z]{1}" or (length_val == "1" and "[A-Za-z]" in pattern_val):
                return "A"
            # [0-9]{1}
            if pattern_val == "[0-9]{1}":
                return "1"
            # [0-9]{1,2}
            if "[0-9]{1,2}" in pattern_val and "]" not in pattern_val.replace("[0-9]{1,2}", ""):
                return "1"
            # [0-9]{2}
            if pattern_val == "[0-9]{2}":
                return "00"
            # .{3} or length 3
            if length_val == "3" and ".{3}" in pattern_val:
                return "000"
            if pattern_val == ".{3}":
                return "000"
            # .{4} .{5} .{8} .{9} .{2} (fixed length)
            if pattern_val == ".{4}":
                return "1234"
            if pattern_val == ".{5}":
                return "12345"
            if pattern_val == ".{8}":
                return "12345678"
            if pattern_val == ".{9}":
                return "123456789"
            if pattern_val == ".{2}":
                return "01"
            # [A-Za-z]{1,3}
            if "[A-Za-z]{1,3}" in pattern_val:
                return "A"
            # [A-Z]* (letters only, can be empty - use "A")
            if pattern_val == "[A-Z]*":
                return "A"
            # .{1,4} .{1,5} etc
            if pattern_val in (".{1,4}", ".{1,5}"):
                return "1"
            if ".{1," in pattern_val and "}" in pattern_val:
                return "1"
            # TIRCarnetNumber-style: ([1-9][0-9]{0,6}|...|25000000|...)
            if "25000000" in pattern_val or "[1-9][0-9]{0,6}" in pattern_val:
                return "1"
            # latitude/longitude
            if "latitude" in str(st_elem).lower() or "[+-]?([0-8]?[0-9]" in pattern_val:
                return "51.50722"
            if "longitude" in str(st_elem).lower() or "180.000000" in pattern_val:
                return "0.12750"

        if length_val == "2" and any(("[A-Z]" in (p.get("value") or "") or "[A-Za-z]" in (p.get("value") or "")) for p in pattern_elems):
            return "GB"
        if length_val == "8" and any("[A-Z]{2}" in (p.get("value") or "") for p in pattern_elems):
            return "GB123456"

        # Pattern 0\.\d*[1-9]\d* (decimal with at least one non-zero after point) - before fractionDigits
        if any("0." in (p.get("value") or "") and "[1-9]" in (p.get("value") or "") for p in pattern_elems):
            return "0.1"

        # fractionDigits: decimal with given decimal places
        frac_elem = restriction.find(f"{{{XS}}}fractionDigits")
        if frac_elem is not None:
            try:
                f = int(frac_elem.get("value") or "0")
                if f == 6:
                    return "0.000000"
                if f == 2:
                    return "0.00"
            except ValueError:
                pass

        # maxLength: use a string that fits (after pattern checks, so email etc. already handled)
        if max_length_val is not None:
            try:
                n = int(max_length_val)
                if n <= 4:
                    return "1" * n if n > 0 else "0"
                if n <= 6:
                    return "123456"[:n]
                return "1" + "0" * (n - 1) if n <= 22 else "1"
            except ValueError:
                pass

        # length=1
        if length_val == "1":
            if any("[0-9]" in (p.get("value") or "") for p in pattern_elems):
                return "1"
            if any("[A-Za-z]" in (p.get("value") or "") for p in pattern_elems) or any("[A-Z0-9]" in (p.get("value") or "") for p in pattern_elems):
                return "A"
            return "1"

    if restriction is not None:
        min_inc = restriction.find(f"{{{XS}}}minInclusive")
        if min_inc is not None and min_inc.get("value") == "1" and base_local in ("integer", "decimal"):
            return "1"
    # Known XSD built-in and custom base type names
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
        "DateTimeType": "2025-03-05T12:00:00",
        "DateType": "2025-03-05",
        "DecimalWithZero_16_2": "0.00",
        "DecimalWithZero_16_6": "0.000000",
        "NumericWithoutZero_5": "1",
        "NumericWithoutZero_1": "1",
        "NumericWithZero_9": "1",
        "NumericWithZero_4": "1",
        "NumericWithZero_8": "1",
    }
    if base_local in samples:
        return samples[base_local]
    # Resolve custom base type (e.g. DateTimeType, MessageTypes, MRNType)
    if types and base_local in types:
        base_elem, _, _ = types[base_local]
        if get_tag(base_elem) == "simpleType":
            return simple_type_sample(base_elem, types)
    return "sample"


def generate_for_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level=0):
    """Generate XML content for a type. Returns list of (tag, content_or_children, attrs, use_prefix)."""
    if type_elem is None:
        return []
    tag = get_tag(type_elem)
    if tag == "complexType":
        return generate_complex_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level)
    if tag == "simpleType":
        return [("__text__", simple_type_sample(type_elem, types), {}, False)]
    return []


def generate_complex_type(ct_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level):
    out = []
    # attributes (direct children of complexType)
    for attr in ct_elem.findall(f"{{{XS}}}attribute"):
        aname = attr.get("name")
        if not aname:
            continue
        default = attr.get("default") or attr.get("fixed")
        if default is not None:
            out.append(("__attr__", aname, default))
        else:
            type_ref = attr.get("type")
            if type_ref:
                type_elem, _ = resolve_type_ref(type_ref, {}, types)
                if type_elem and get_tag(type_elem) == "simpleType":
                    out.append(("__attr__", aname, simple_type_sample(type_elem, types)))
                else:
                    out.append(("__attr__", aname, "sample"))
            else:
                out.append(("__attr__", aname, "sample"))
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
