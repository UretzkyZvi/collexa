# Ensure 'app' package is importable when running pytest from backend/app
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))  # backend/app
BACKEND_ROOT = os.path.dirname(ROOT)  # backend
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Reuse global fixtures from backend/tests/conftest.py if needed
try:
    from backend.tests.conftest import *  # noqa: F401,F403
except Exception:
    pass
