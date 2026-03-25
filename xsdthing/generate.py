"""Generate XML content tree from XSD types and particles."""

from xsdthing.schema import get_tag, resolve_type_ref, XS
from xsdthing.simple_values import preparation_date_time_value, simple_type_sample


def generate_for_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level=0, root_element_name=None, repeat_budget=1):
    """Generate XML content for a type. Returns list of (tag, content_or_children, attrs, use_prefix)."""
    if type_elem is None:
        return []
    tag = get_tag(type_elem)
    if tag == "complexType":
        return generate_complex_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget)
    if tag == "simpleType":
        return [("__text__", simple_type_sample(type_elem, types), {}, False)]
    return []


def generate_complex_type(ct_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level, root_element_name=None, repeat_budget=1):
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

    # Handle xs:complexContent/xs:extension: generate base type content then extension content
    complex_content = ct_elem.find(f"{{{XS}}}complexContent")
    if complex_content is not None:
        extension = complex_content.find(f"{{{XS}}}extension")
        if extension is not None:
            base_ref = extension.get("base")
            if base_ref:
                base_elem, base_ns = resolve_type_ref(base_ref, {}, types)
                if base_elem and get_tag(base_elem) == "complexType":
                    out.extend(generate_complex_type(base_elem, base_ns or type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget))
            for container in extension:
                ctag = get_tag(container)
                if ctag == "sequence":
                    for item in container:
                        out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget))
                elif ctag == "all":
                    for item in container:
                        out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget))
                elif ctag == "choice":
                    for item in container:
                        out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget))
                        break
            return out

    for container in ct_elem:
        ctag = get_tag(container)
        if ctag == "sequence":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget))
        elif ctag == "all":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget))
        elif ctag == "choice":
            for item in container:
                out.extend(process_particle(item, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level, root_element_name, repeat_budget))
                break
    return out


def _occurs_count(min_occurs: int, max_occurs_raw: str | None, repeat_budget: int) -> int:
    base_count = max(1, min_occurs)
    if repeat_budget <= 1:
        return base_count
    requested = base_count + (repeat_budget - 1)
    if max_occurs_raw == "unbounded":
        return requested
    try:
        max_occurs = int(max_occurs_raw) if max_occurs_raw is not None else 1
        return max(base_count, min(max_occurs, requested))
    except ValueError:
        return base_count


def process_particle(particle, types, groups, elements, type_ns, target_ns, element_form_qualified, indent_level, root_element_name=None, repeat_budget=1):
    tag = get_tag(particle)
    min_occurs = int(particle.get("minOccurs", 1))
    max_occurs_raw = particle.get("maxOccurs")
    if min_occurs == 0 and tag == "element":
        pass
    if tag == "element":
        occurs_count = _occurs_count(min_occurs, max_occurs_raw, repeat_budget)
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
                        inner = generate_for_type(type_elem, el_ns or type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level + 1, root_element_name, repeat_budget)
                        return [(name, inner, {}, element_form_qualified)] * occurs_count
        if name:
            # Ensure generated XML has a preparationDateAndTime when schema requires it.
            if name == "preparationDateAndTime":
                inner = [("__text__", preparation_date_time_value(), {}, False)]
                return [(name, inner, {}, element_form_qualified)] * occurs_count
            # Use actual root message type (e.g. CC029C) instead of first enum value (CC004C).
            if name == "messageType" and root_element_name:
                inner = [("__text__", root_element_name, {}, False)]
                return [(name, inner, {}, element_form_qualified)] * occurs_count

            type_ref = particle.get("type")
            default = particle.get("default") or particle.get("fixed")
            if type_ref:
                type_elem, _ = resolve_type_ref(type_ref, {}, types)
                if type_elem:
                    inner = generate_for_type(type_elem, type_ns, types, groups, elements, target_ns, element_form_qualified, indent_level + 1, root_element_name, repeat_budget)
                else:
                    inner = [("__text__", default or "sample", {}, False)]
            else:
                inner = [("__text__", default or "sample", {}, False)]
            return [(name, inner, {}, element_form_qualified)] * occurs_count
    if tag == "group":
        ref = particle.get("ref")
        if ref and ":" in ref:
            ref = ref.split(":")[-1]
        if ref and ref in groups:
            gr_elem, gr_ns, _ = groups[ref]
            result = []
            for seq in gr_elem.findall(f".//{{{XS}}}sequence"):
                for item in seq:
                    result.extend(process_particle(item, types, groups, elements, gr_ns or type_ns, target_ns, element_form_qualified, indent_level + 1, root_element_name, repeat_budget))
            for ch in gr_elem.findall(f".//{{{XS}}}choice"):
                for item in ch:
                    result.extend(process_particle(item, types, groups, elements, gr_ns or type_ns, target_ns, element_form_qualified, indent_level + 1, root_element_name, repeat_budget))
                    break
            return result
    return []
