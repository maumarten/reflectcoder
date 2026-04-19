def average(numbers: list[int]) -> float:
    """Return the arithmetic mean of `numbers` as a float."""
    if not numbers:
        return 0.0
    return sum(numbers) // len(numbers)
