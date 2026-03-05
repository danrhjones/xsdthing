"""
Sample values for XSD simple types.
Pattern rules are applied in order; first match wins.
"""

from xsdthing.schema import get_tag, XS


# Built-in and custom type name -> sample value (fallback when no pattern matches)
BASE_SAMPLES = {
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
    "base64Binary": "AQIDBA==",
    "positiveInteger": "1",
    "nonNegativeInteger": "0",
    "DateTimeType": "2025-03-05T12:00:00",
    "DateType": "2025-03-05",
    "DecimalWithZero_16_2": "0.00",
    "DecimalWithZero_16_6": "0.000000",
    "DecimalWithoutZero_16_2": "0.01",
    "DecimalWithoutZero_16_6": "0.1",
    "NumericWithoutZero_1": "1",
    "NumericWithoutZero_3": "1",
    "NumericWithoutZero_5": "1",
    "NumericWithoutZero_8": "1",
    "NumericWithZero_3": "1",
    "NumericWithZero_4": "1",
    "NumericWithZero_8": "1",
    "NumericWithZero_9": "1",
    "DeclarationGoodsItemNumberType": "1",
    "DeclarationGoodsItemNumberType_WithZero": "0",
    "AES-P1_DeclarationGoodsItemNumberType": "1",
    "NCTS-P5_DeclarationGoodsItemNumberType": "1",
    "Base64Binary": "AQIDBA==",
}


def _pattern_matches(pv: str, *substrings: str) -> bool:
    """True if all substrings appear in pattern value pv."""
    return all(s in pv for s in substrings)


def simple_type_sample(st_elem, types: dict) -> str:
    """Return a sample value for a simpleType (enumeration first, then restriction base/pattern/length)."""
    if st_elem is None:
        return "sample"

    for enum in st_elem.findall(f".//{{{XS}}}enumeration"):
        val = enum.get("value")
        if val is not None:
            return val

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

    if restriction is None:
        return _fallback_sample(base_local, types)

    length_elem = restriction.find(f"{{{XS}}}length")
    max_length_elem = restriction.find(f"{{{XS}}}maxLength")
    pattern_elems = restriction.findall(f"{{{XS}}}pattern")
    length_val = length_elem.get("value") if length_elem is not None else None
    max_length_val = max_length_elem.get("value") if max_length_elem is not None else None

    # MRN preference: if type has both legacy and NCTS-P5/Transit patterns, prefer the newer ones
    all_pvs = [p.get("value") or "" for p in pattern_elems]
    if any("[J-M][0-9]" in pv and "[A-Z0-9]{12}" in pv for pv in all_pvs):
        return "24GB123456789012K1"
    if any("[A-E][0-9]" in pv and "[A-Z0-9]{12}" in pv for pv in all_pvs):
        return "24AB123456789012A0"

    # Single pass over patterns (order matters for other rules)
    for pattern_elem in pattern_elems:
        pv = pattern_elem.get("value") or ""
        # Email
        if "@" in pv:
            return "user@example.com"
        # Legacy MRN / GRN (NCTS-P5 and Transit already handled by pre-scan)
        if "[A-Z0-9]{13}[0-9]" in pv:
            return "24AB1234567890123"
        if "[0-9]{2}[A-Z]{2}[A-Z0-9]{12}[0-9]" in pv:
            return "24GB1234567890123"
        # identificationNumber, currency, letters
        if "[A-Z]{2}[!-~]" in pv:
            return "GB12345678901"
        if pv.strip() == "[A-Za-z]{3}" or (length_val == "3" and "[A-Za-z]" in pv):
            return "EUR"
        # Two letters (pattern or length+pattern) — unified
        if (pv == "[A-Za-z]{2}" or (length_val == "2" and ("[A-Z]" in pv or "[A-Za-z]" in pv))):
            return "GB"
        if pv == "[A-Za-z]{1}" or (length_val == "1" and "[A-Za-z]" in pv):
            return "A"
        # Digits
        if pv == "[0-9]{1}":
            return "1"
        if "[0-9]{1,2}" in pv and "]" not in pv.replace("[0-9]{1,2}", ""):
            return "1"
        if pv == "[0-9]{2}":
            return "00"
        # Fixed length .{n}
        if (length_val == "3" and ".{3}" in pv) or pv == ".{3}":
            return "000"
        if pv == ".{4}":
            return "1234"
        if pv == ".{5}":
            return "12345"
        if pv == ".{8}":
            return "12345678"
        if pv == ".{9}":
            return "123456789"
        if pv == ".{2}":
            return "01"
        if "[A-Za-z]{1,3}" in pv:
            return "A"
        if pv in ("[A-Z]*", "[A-Z0-9]*"):
            return "A"
        if pv in (".{1,4}", ".{1,5}") or (".{1," in pv and "}" in pv):
            return "1"
        if "25000000" in pv or "[1-9][0-9]{0,6}" in pv:
            return "1"
        if _pattern_matches(pv, "[C][T][0-9]", "[A-Z]{2}[A-Z0-9]{11}"):
            return "24GB12345678901CT0"
        if pv == ".{19}":
            return "2025-03-05T12:00:00"
        if "[2][0][1-9][0-9]" in pv or pv == "[2][0][1-9][0-9]":
            return "2025"
        if pv == ".{1}":
            return "1"
        if pv == ".{10}":
            return "2025-03-05"
        if "[!-~]" in pv and pv.endswith("E"):
            return "1E"
        if "latitude" in str(st_elem).lower() or "[+-]?([0-8]?[0-9]" in pv:
            return "51.50722"
        if "longitude" in str(st_elem).lower() or "180.000000" in pv:
            return "0.12750"

    # Length + pattern (any matching pattern in list)
    if length_val == "2" and any("[A-Z]" in (p.get("value") or "") or "[A-Za-z]" in (p.get("value") or "") for p in pattern_elems):
        return "GB"
    if length_val == "8" and any("[A-Z]{2}" in (p.get("value") or "") for p in pattern_elems):
        return "GB123456"

    # Decimal without zero (0.1)
    if any(("0." in (pv := (p.get("value") or "")) or "0\\." in pv) and "[1-9]" in pv for p in pattern_elems):
        return "0.1"

    # fractionDigits
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

    # maxLength
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

    # length + custom base: recurse then truncate/pad
    if length_val and base_local in types:
        base_elem, _, _ = types[base_local]
        if get_tag(base_elem) == "simpleType":
            try:
                n = int(length_val)
                base_val = simple_type_sample(base_elem, types)
                if len(base_val) >= n:
                    return base_val[:n]
                return (base_val + (base_val[0] if base_val else "A") * n)[:n]
            except ValueError:
                pass

    if length_val == "1":
        if any("[0-9]" in (p.get("value") or "") for p in pattern_elems):
            return "1"
        if any("[A-Za-z]" in (p.get("value") or "") or "[A-Z0-9]" in (p.get("value") or "") for p in pattern_elems):
            return "A"
        return "1"

    return _fallback_sample(base_local, types, restriction)


def _fallback_sample(base_local: str, types: dict, restriction=None) -> str:
    """minInclusive(1), base name lookup, or recurse."""
    if restriction is not None:
        min_inc = restriction.find(f"{{{XS}}}minInclusive")
        if min_inc is not None and min_inc.get("value") == "1" and base_local in ("integer", "decimal"):
            return "1"

    if base_local in BASE_SAMPLES:
        return BASE_SAMPLES[base_local]

    if types and base_local in types:
        base_elem, _, _ = types[base_local]
        if get_tag(base_elem) == "simpleType":
            return simple_type_sample(base_elem, types)

    return "sample"
