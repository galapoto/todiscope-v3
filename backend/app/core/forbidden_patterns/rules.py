def _tok(*chars: str) -> str:
    return "".join(chars)


FORBIDDEN_TOKENS_IN_CORE = (
    _tok("f", "i", "n", "a", "n", "c", "e"),
    _tok("f", "i", "n", "a", "n", "c", "i", "a", "l"),
    _tok("c", "s", "r", "d"),
    _tok("e", "s", "r", "s"),
    _tok("a", "u", "d", "i", "t"),
    _tok("i", "n", "s", "u", "r", "a", "n", "c", "e"),
    _tok("c", "o", "n", "s", "t", "r", "u", "c", "t", "i", "o", "n"),
    _tok("c", "a", "p", "i", "t", "a", "l"),
    _tok("l", "o", "a", "n"),
)
