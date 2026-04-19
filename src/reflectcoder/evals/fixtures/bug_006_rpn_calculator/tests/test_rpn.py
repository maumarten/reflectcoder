import pytest

from rpn import rpn_eval


def test_simple_addition():
    assert rpn_eval(["2", "3", "+"]) == 5.0


def test_true_division_returns_float():
    assert rpn_eval(["6", "4", "/"]) == 1.5


def test_mixed_operations():
    # (5 + 3) * 2 = 16
    assert rpn_eval(["5", "3", "+", "2", "*"]) == 16.0


def test_float_literal_token():
    assert rpn_eval(["3.5", "0.5", "+"]) == 4.0


def test_insufficient_operands_raises_valueerror():
    with pytest.raises(ValueError) as exc:
        rpn_eval(["1", "+"])
    assert str(exc.value) == "insufficient operands"


def test_insufficient_operands_empty_stack():
    with pytest.raises(ValueError) as exc:
        rpn_eval(["+"])
    assert str(exc.value) == "insufficient operands"


def test_extra_operands_raises_valueerror():
    with pytest.raises(ValueError) as exc:
        rpn_eval(["1", "2", "3", "+"])
    assert str(exc.value) == "expression leaves more than one value"


def test_empty_expression_raises_valueerror():
    with pytest.raises(ValueError) as exc:
        rpn_eval([])
    assert str(exc.value) == "empty expression"


def test_unknown_token_raises_valueerror_with_token():
    with pytest.raises(ValueError) as exc:
        rpn_eval(["1", "2", "foo"])
    assert str(exc.value) == "unknown token: foo"
