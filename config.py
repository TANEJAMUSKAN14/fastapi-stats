# ==========================================
# MASTER CONFIGURATION CHEAT SHEET
# Fill these in with your unique assigned values from the Exam Portal!
# ==========================================

# 1. Your IITM Email
EMAIL = "your_email@example.com"

# 2. Q1: CORS Allowed Origin
Q1_ALLOWED_ORIGIN = "https://app-xxxxxx.example.com"

# 3. Q2: OAuth JWKS (Issuer, Audience, and Public Key)
ISSUER = "https://idp.exam.local"
AUDIENCE = "..."
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
... (Paste your full key here) ...
-----END PUBLIC KEY-----"""

# 4. Q3: 12-Factor Config (Manually merge the variables)
Q3_PORT = 8000
Q3_WORKERS = 1
Q3_DEBUG = False
Q3_LOG_LEVEL = "info"

# 5. Q5: Analytics (Find the API key in the Q5 instruction tab)
Q5_API_KEY = "ak_..."

# 6. Q9: Idempotency & Rate Limit (Find total orders and rate limit)
Q9_TOTAL_ORDERS = 50
Q9_RATE_LIMIT = 15

# 7. Q10: Middleware Rate Limit (Find allowed origin and rate limit)
Q10_ALLOWED_ORIGIN = "https://app-xxxxxx.example.com"
Q10_RATE_LIMIT = 8

# ==========================================
# FIXED VARIABLES (Do not change these)
# ==========================================
EXAM_PORTAL_ORIGIN = "https://exam.sanand.workers.dev"
