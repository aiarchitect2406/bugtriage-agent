"""Configuration and Secret Management for Google ADK 2.0 Bug Triage Agent."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from google.cloud import secretmanager
    HAS_SECRET_MANAGER = True
except ImportError:
    HAS_SECRET_MANAGER = False

class Config:
    """System configuration and Model Routing constants adhering to ADK 2.0."""
    
    REPO_NAME: str = os.getenv("TARGET_REPO", "aiarchitect2406/example-payment-svc")
    TARGET_REPO_URL: str = os.getenv("TARGET_REPO_URL", "https://github.com/aiarchitect2406/example-payment-svc.git")
    TARGET_REPO_NAME: str = os.getenv("TARGET_REPO_NAME", "aiarchitect2406/example-payment-svc")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "aiarchitect2406/example-payment-svc")
    LOCAL_TARGET_REPO_PATH: str = os.getenv("LOCAL_TARGET_REPO_PATH", "./target_repo")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID", "your-gcp-project-id"))
    LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    
    # Model Routing Constants (Vertex AI & Multi-Model Ensemble)
    FAST_MODEL: str = os.getenv("FAST_MODEL", "gemini-3.7-flash")
    REASONING_MODEL: str = os.getenv("REASONING_MODEL", "gemini-3.1-pro-preview")
    REVIEWER_MODEL: str = os.getenv("REVIEWER_MODEL", "claude-sonnet-4-6")
    ANTHROPIC_LOCATION: str = os.getenv("ANTHROPIC_LOCATION", "global")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Session & Memory
    SESSIONS_ID: str = os.getenv("SESSIONS_ID", "bug-triage-sessions-v1")
    MEMORY_BANK_ID: str = os.getenv("MEMORY_BANK_ID", "bug-triage-memory-v1")
    AGENT_ENGINE_ID: str = os.getenv("AGENT_ENGINE_ID", "bug-triage-engine-001")
    
    # Thresholds & Security
    DUPLICATE_SIMILARITY_THRESHOLD: float = float(os.getenv("DUPLICATE_THRESHOLD", "0.85"))
    HMAC_SECRET_KEY: str = os.getenv("HITL_HMAC_SECRET", "super-secret-hitl-hmac-key")

    @classmethod
    def get_secret(cls, secret_id: str, default: Optional[str] = None) -> str:
        """Fetch secret from Google Cloud Secret Manager or environment variable."""
        env_val = os.getenv(secret_id.upper().replace("-", "_"))
        if env_val:
            return env_val

        if HAS_SECRET_MANAGER and cls.PROJECT_ID not in ["your-gcp-project-id", ""]:
            try:
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{cls.PROJECT_ID}/secrets/{secret_id}/versions/latest"
                response = client.access_secret_version(request={"name": name}, timeout=2.0)
                return response.payload.data.decode("UTF-8").strip()
            except Exception as e:
                logging.debug(f"Secret Manager not reachable for '{secret_id}': {e}")

        if default is not None:
            return default
        return f"mock-{secret_id}-key"
