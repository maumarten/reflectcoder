def normalize_path(path: str) -> str:
    """Normalize a POSIX-style path string."""
    absolute = path.startswith("/")
    parts = path.split("/")
    out = []
    for p in parts:
        if p == "" or p == ".":
            continue
        if p == "..":
            out.pop()
        else:
            out.append(p)
    result = "/".join(out)
    if absolute:
        result = "/" + result
    return result
