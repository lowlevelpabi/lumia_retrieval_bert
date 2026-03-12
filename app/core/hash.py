from hashids import Hashids
import os
from dotenv import load_dotenv

load_dotenv()

# We use a mix of uppercase, lowercase, and numbers
# The salt makes it unique to this app, keeping the IDs unpredictable
HASH_SALT = os.getenv("HASH_SALT", "lumia-thesis-secret-salt")
MIN_HASH_LENGTH = 16

hashids = Hashids(salt=HASH_SALT, min_length=MIN_HASH_LENGTH)

def encode_id(db_id: int) -> str:
    """Encodes a numeric database ID into a long hash string."""
    return hashids.encode(db_id)

def decode_id(hash_str: str) -> int | None:
    """Decodes a hash string back into a numeric database ID. Returns None if invalid."""
    decoded = hashids.decode(hash_str)
    if decoded and len(decoded) > 0:
        return decoded[0]
    return None
