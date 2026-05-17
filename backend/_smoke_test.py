"""Temporary smoke test for auth utilities."""
import os
from datetime import timedelta

import bcrypt

os.environ["JWT_SECRET"] = "test-secret-key"
_hash = bcrypt.hashpw(b"mypassword", bcrypt.gensalt()).decode()
os.environ["CMS_PASSWORD_HASH"] = _hash

from app.auth import create_access_token, verify_password, verify_token  # noqa: E402

# verify_password
assert verify_password("mypassword", _hash), "correct password should pass"
assert not verify_password("wrongpassword", _hash), "wrong password should fail"

# create_access_token / verify_token round-trip
token = create_access_token("author", timedelta(hours=1))
payload = verify_token(token)
assert payload["sub"] == "author", f"expected sub=author, got {payload['sub']}"

# expired token raises 401
expired_token = create_access_token("author", timedelta(seconds=-1))
try:
    verify_token(expired_token)
    assert False, "should have raised"
except Exception as exc:
    msg = str(exc).lower()
    assert "401" in msg or "validate" in msg or "unauthorized" in msg, f"unexpected: {exc}"

print("All smoke tests passed")
