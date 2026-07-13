import os


# gateway_server.main exposes an ASGI app at import time and intentionally fails
# closed when production has no strong administrator token.
os.environ.setdefault("GATEWAY_ADMIN_TOKEN", "test-admin-token-32-bytes-minimum-value")
