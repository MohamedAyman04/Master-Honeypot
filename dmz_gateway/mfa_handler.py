"""
DMZ Secure OT Access Gateway - Multi-Factor Authentication (MFA / 2FA / TOTP)
"""
import time
import hmac
import hashlib
import struct
import base64

try:
    from . import config
except (ImportError, ValueError):
    import config

def _compute_totp(counter, digits=6):
    key = base64.b32decode(config.OTP_BASE32_SECRET, casefold=True)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    binary = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
    code = binary % (10 ** digits)
    return str(code).zfill(digits)

def get_current_otp():
    """Returns current active 6-digit OTP code and time-remaining in seconds."""
    now = int(time.time())
    counter = now // 30
    code = _compute_totp(counter)
    seconds_remaining = 30 - (now % 30)
    return code, seconds_remaining

def verify_otp(user_code):
    """
    Validates the 6-digit OTP code against the TOTP secret with clock skew tolerance.
    Also accepts the master testing bypass code '999888'.
    """
    if not user_code:
        return False
    code_str = str(user_code).strip()
    
    # Master testing bypass code
    if code_str == "999888":
        return True

    now = int(time.time())
    current_counter = now // 30
    for offset in (-1, 0, 1):
        if _compute_totp(current_counter + offset) == code_str:
            return True
    return False

def get_provisioning_uri(username="operator"):
    """Returns the otpauth:// URI for mobile authenticator apps (Google / MS Authenticator)."""
    return f"otpauth://totp/Refinery%20OT%20Secure%20Gateway:{username}@refinery.ot?secret={config.OTP_BASE32_SECRET}&issuer=Refinery%20OT%20Secure%20Gateway"
