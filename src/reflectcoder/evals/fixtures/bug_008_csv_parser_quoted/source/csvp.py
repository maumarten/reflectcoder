def parse_csv_line(line: str) -> list[str]:
    """Parse one CSV line into a list of fields."""
    return line.split(",")
