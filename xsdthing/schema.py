"""XSD schema parsing and type resolution."""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

XS = "http://www.w3.org/2001/XMLSchema"

# Set to True to print include resolution (e.g. XSDTHING_DEBUG=1 ./xsd2sample.sh ...)
_debug = os.environ.get("XSDTHING_DEBUG", "").lower() in ("1", "yes", "true")


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
    path = path.resolve()
    tree = ET.parse(path)
    root = tree.getroot()

    ns = root.get("targetNamespace") or ""
    if path not in target_ns:
        target_ns[path] = ns

    for inc in root.findall(f".//{{{XS}}}include"):
        loc = inc.get("schemaLocation")
        if not loc:
            continue
        # Resolve relative to the *including* file's directory (XSD spec: relative to document base URI)
        included = (path.parent / loc).resolve()
        if not included.exists():
            if _debug:
                print(f"[xsdthing] include ignored (file not found): {loc!r} from {path} -> {included}", file=sys.stderr)
            continue
        if _debug:
            print(f"[xsdthing] include: {path.name} -> {included.name}", file=sys.stderr)
        if included not in target_ns:
            parse_schema(included, base_dir, types, groups, elements, target_ns)

    for ct in root:
        if get_tag(ct) == "complexType" and ct.get("name"):
            types[ct.get("name")] = (ct, ns, path)

    for st in root:
        if get_tag(st) == "simpleType" and st.get("name"):
            types[st.get("name")] = (st, ns, path)

    for gr in root:
        if get_tag(gr) == "group" and gr.get("name"):
            groups[gr.get("name")] = (gr, ns, path)

    for el in root:
        if get_tag(el) == "element" and el.get("name"):
            name = el.get("name")
            elements[name] = (el, ns, path)


def resolve_type_ref(type_ref: str, ns_map: dict, types: dict) -> tuple:
    """Resolve 'TypeName' or 'prefix:TypeName' to (elem, ns)."""
    if ":" in type_ref:
        _prefix, name = type_ref.split(":", 1)
        for tname, (elem, ns, _) in types.items():
            if tname == name:
                return (elem, ns)
        return (None, None)
    for tname, (elem, ns, _) in types.items():
        if tname == type_ref:
            return (elem, ns)
    return (None, None)
