def flatten(items: list) -> list:
    """Flatten a nested list of integers into a single flat list."""
    result: list = []
    for item in items:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result
