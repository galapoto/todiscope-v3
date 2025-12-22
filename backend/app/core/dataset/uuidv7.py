import secrets
import time
import uuid


def uuid7() -> uuid.UUID:
    """
    Generate a UUIDv7 (time-ordered) UUID.
    Minimal implementation sufficient for IDs; relies on current time in milliseconds.
    """
    ts_ms = int(time.time() * 1000)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)

    # UUIDv7 layout (draft):
    # 48 bits unix_ts_ms | 4 bits ver(7) | 12 bits rand_a | 2 bits var | 62 bits rand_b
    value = (ts_ms & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76
    value |= (rand_a & ((1 << 12) - 1)) << 64
    value |= 0x2 << 62  # RFC4122 variant
    value |= rand_b & ((1 << 62) - 1)
    return uuid.UUID(int=value)

