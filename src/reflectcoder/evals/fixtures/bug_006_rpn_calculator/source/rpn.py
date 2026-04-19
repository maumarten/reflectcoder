_OPS = {"+", "-", "*", "/"}


def rpn_eval(tokens):
    """Evaluate a list of RPN tokens and return a float."""
    stack = []
    for tok in tokens:
        if tok in _OPS:
            b = stack.pop()
            a = stack.pop()
            if tok == "+":
                stack.append(a + b)
            elif tok == "-":
                stack.append(a - b)
            elif tok == "*":
                stack.append(a * b)
            else:
                stack.append(a / b)
        else:
            stack.append(float(tok))
    return stack[0]
