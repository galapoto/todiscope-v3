def validate_engine_name(engine_name: str) -> None:
    if not isinstance(engine_name, str):
        raise ValueError("Engine name must be a string")
    if not engine_name.islower():
        raise ValueError("Engine name must be lowercase")
    if not engine_name.replace('_', '').isalpha():
        raise ValueError("Engine name can only contain letters and underscores")
    if not engine_name[0].isalpha():
        raise ValueError("Engine name must start with a letter")
    if not (3 <= len(engine_name) <= 40):
        raise ValueError("Engine name must be between 3 and 40 characters")
