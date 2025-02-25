import hashlib
import time
import random
from typing import Dict, Any

class FakeLogin:
    _cache: Dict[str, Dict[str, Any]] = {}  # Class-level session cache

    @classmethod
    def generate_session_id(cls, username: str, password: str, company_id: str) -> str:
        """Generate a unique session ID using a hash of user credentials and a timestamp."""
        session_data = f"{username}:{password}:{company_id}:{time.time()}{random.randint(1000, 9999)}"
        return hashlib.sha256(session_data.encode()).hexdigest()

    @classmethod
    def login(cls, parameters: Dict[str, str]) -> Dict[str, Any]:
        """Simulate user login and return a structured response with session ID and status code."""
        username = parameters.get("username")
        password = parameters.get("password")
        company_id = parameters.get("CompanyID")

        if not all([username, password, company_id]):
            return {"status": 400, "message": "Missing required parameters: username, password, or CompanyID"}

        session_id = cls.generate_session_id(username, password, company_id)
        cls._cache[session_id] = {
            "username": username,
            "company_id": company_id,
            "expires_at": time.time() + 1800  # Session valid for 30 minutes
        }

        return {
            "status": 200,
            "session_id": session_id,
            "message": "Login successful"
        }
