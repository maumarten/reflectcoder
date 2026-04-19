def parse_query_string(qs: str) -> dict[str, str]:
    """Parse a URL query string into a dict (later values win on duplicate keys)."""
    result: dict[str, str] = {}
    for pair in qs.split("&"):
        k, v = pair.split("=")
        result[k] = v
    return result
