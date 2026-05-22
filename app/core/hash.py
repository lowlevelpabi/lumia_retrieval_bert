from hashids import Hashids
import os
from dotenv import load_dotenv

load_dotenv()

# --- Legacy Alphanumeric Config (Hashids) ---
HASH_SALT = os.getenv("HASH_SALT", "lumia-thesis-secret-salt")
MIN_HASH_LENGTH = 16
hashids_legacy = Hashids(salt=HASH_SALT, min_length=MIN_HASH_LENGTH)

# --- Modern 12-Digit Numeric Config ---
# Reversible mapping: (ID * P) % M + OFFSET
# M = 900B ensures the range [0, 900B)
# Adding 100B ensures the result is in [100B, 1000B), i.e., exactly 12 digits.
M = 900_000_000_000
P = 462746274623
P_INV = 134484458687
OFFSET = 100_000_000_000

def encode_id(db_id: int) -> str:
    """Encodes a numeric database ID into a 12-digit numeric string."""
    if db_id < 0:
        return hashids_legacy.encode(db_id) # Fallback for negative if any
    
    # Linear congruential shuffle
    shuffled = (db_id * P) % M
    numeric_id = shuffled + OFFSET
    return str(numeric_id)

def decode_id(id_str: str) -> int | None:
    """
    Decodes an ID string back into a numeric database ID.
    Supports both new 12-digit numeric IDs and legacy alphanumeric Hashids.
    """
    if not id_str:
        return None

    # 1. Try modern 12-digit numeric decode
    if id_str.isdigit() and len(id_str) == 12:
        try:
            val = int(id_str)
            if val >= OFFSET:
                shuffled = val - OFFSET
                db_id = (shuffled * P_INV) % M
                return db_id
        except (ValueError, TypeError):
            pass

    # 2. Try legacy alphanumeric Hashids decode
    decoded = hashids_legacy.decode(id_str)
    if decoded and len(decoded) > 0:
        return decoded[0]
    
    # 3. Last resort: check if it's already a raw integer (for internal dev use)
    if id_str.isdigit() and len(id_str) < 10:
        return int(id_str)

    return None
