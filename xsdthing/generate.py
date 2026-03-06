"""Generate XML content tree from XSD types and particles."""

from xsdthing.schema import get_tag, resolve_type_ref, XS
from xsdthing.simple_values import preparation_date_time_value, simple_type_sample


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

    for container in ct_elem:
        ctag = get_tag(container)
        if ctag == "sequence":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level))
        elif ctag == "all":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level))
        elif ctag == "choice":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level))
                break
    return out


def process_particle(particle, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level):
    tag = get_tag(particle)
    min_occurs = int(particle.get("minOccurs", 1))
    if min_occurs == 0 and tag == "element":
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
            # Ensure generated XML has a preparationDateAndTime when schema requires it.
            # Use current system datetime in XSD dateTime format; fallback to fixed sample.
            if name == "preparationDateAndTime":
                inner = [("__text__", preparation_date_time_value(), {}, False)]
                return [(name, inner, {}, element_form_qualified)]

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
