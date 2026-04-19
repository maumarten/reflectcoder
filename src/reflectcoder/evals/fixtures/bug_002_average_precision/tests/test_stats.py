from stats import average


def test_integer_result():
    assert average([2, 4]) == 3.0


def test_fractional_result():
    assert abs(average([1, 2]) - 1.5) < 1e-9


def test_empty_list():
    assert average([]) == 0.0


def test_single_element():
    assert average([7]) == 7.0


def test_returns_float():
    assert isinstance(average([1, 2, 3]), float)
