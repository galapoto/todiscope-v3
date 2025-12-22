import hashlib


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_sha256(data: bytes, expected_sha256_hex: str) -> None:
    actual = sha256_hex(data)
    if actual != expected_sha256_hex:
        raise ValueError("SHA256_MISMATCH")

