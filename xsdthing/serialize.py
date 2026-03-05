"""Serialize generated content tree to XML string."""


def serialize(node, ns_uri, prefix, qualified, indent=0):
    """Node is (name, content_list, attrs_dict, use_prefix). content_list items are (name, content, attrs, q) or ('__text__', value, {}, _) or ('__attr__', aname, value)."""
    if node[0] == "__text__":
        return str(node[1])
    if node[0] == "__attr__":
        return None
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
