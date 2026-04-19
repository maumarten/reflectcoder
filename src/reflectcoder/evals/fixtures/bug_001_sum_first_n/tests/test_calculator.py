from calculator import sum_first_n


def test_sum_first_5():
    assert sum_first_n(5) == 15


def test_sum_first_1():
    assert sum_first_n(1) == 1


def test_sum_first_100():
    assert sum_first_n(100) == 5050


def test_sum_zero():
    assert sum_first_n(0) == 0
