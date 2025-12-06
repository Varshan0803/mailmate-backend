# test_hash.py
from app.core.security import hash_password, verify_password
tests = [
    "abc12345",
    "test1234",
    "a" * 200,                    # very long ascii
    "pa ss 💥 with emoji",        # contains emoji + spaces
    "zero\u200Bwidth",            # contains zero-width space
]

for p in tests:
    h = hash_password(p)
    ok = verify_password(p, h)
    print(f"plain: {repr(p)[:60]:60}  -> hash_len: {len(h):3}  verify: {ok}")
