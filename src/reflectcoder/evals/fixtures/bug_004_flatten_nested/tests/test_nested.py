from nested import flatten


def test_already_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]


def test_one_level():
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def test_deeply_nested():
    assert flatten([1, [2, [3, [4, 5]]], 6]) == [1, 2, 3, 4, 5, 6]


def test_nested_empty_lists():
    assert flatten([[], [[]], [1]]) == [1]


def test_empty_input():
    assert flatten([]) == []


def test_single_deep_branch():
    assert flatten([[[[[42]]]]]) == [42]
