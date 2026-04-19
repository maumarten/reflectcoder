from accumulator import append_item


def test_fresh_bucket_each_call():
    a = append_item(1)
    b = append_item(2)
    assert a == [1]
    assert b == [2]


def test_explicit_bucket_is_mutated_in_place():
    base: list[int] = []
    append_item(1, base)
    append_item(2, base)
    assert base == [1, 2]


def test_different_explicit_buckets_are_independent():
    a: list[int] = []
    b: list[int] = []
    append_item("x", a)
    append_item("y", b)
    assert a == ["x"]
    assert b == ["y"]
