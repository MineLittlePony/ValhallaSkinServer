import sys

import httpcore2
import httpx2

sys.modules["httpx"] = httpx2
sys.modules["httpcore"] = httpcore2
