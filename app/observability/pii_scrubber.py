"""Enterprise PII & Secret Scrubbing Engine combining Google Cloud DLP API and Regex Fallback."""

import re
import logging
from typing import Tuple
from app.config import Config

try:
    from google.cloud import dlp_v2
    HAS_DLP_API = True
except ImportError:
    HAS_DLP_API = False

class EnterprisePIIRedactor:
    """Scrubs sensitive PII (emails, tokens, passwords, IPs, credit cards) from text payloads."""
    
    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    API_KEY_REGEX = re.compile(r'(?:api_key|token|bearer|secret|password)[=:\s]+[A-Za-z0-9_\-]{12,}', re.IGNORECASE)
    IPV4_REGEX = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    CREDIT_CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')

    @classmethod
    def redact_text(cls, text: str) -> Tuple[str, int]:
        """Redacts sensitive PII from string text.
        
        Returns:
            Tuple[str, int]: (Sanitized text string, Redacted token count)
        """
        if not text:
            return text, 0

        redacted_count = 0

        if HAS_DLP_API:
            try:
                dlp_client = dlp_v2.DlpServiceClient()
                parent = f"projects/{Config.PROJECT_ID}"
                
                info_types = [
                    {"name": "EMAIL_ADDRESS"},
                    {"name": "IP_ADDRESS"},
                    {"name": "AUTH_TOKEN"},
                    {"name": "CREDIT_CARD_NUMBER"},
                    {"name": "API_KEY"},
                ]
                
                inspect_config = {"info_types": info_types}
                deidentify_config = {
                    "info_type_transformations": {
                        "transformations": [
                            {"primitive_transformation": {"replace_config": {"new_value": {"string_value": "[REDACTED_DLP]"}}}}
                        ]
                    }
                }
                
                item = {"value": text}
                response = dlp_client.deidentify_content(
                    request={
                        "parent": parent,
                        "deidentify_config": deidentify_config,
                        "inspect_config": inspect_config,
                        "item": item,
                    }
                )
                scrubbed_val = response.item.value
                redacted_count = text.count("[REDACTED_DLP]")
                return scrubbed_val, max(redacted_count, 1 if scrubbed_val != text else 0)
            except Exception as e:
                logging.warning(f"DLP API call failed ({e}), falling back to Regex scrubber.")

        scrubbed = text
        email_matches = len(cls.EMAIL_REGEX.findall(scrubbed))
        scrubbed = cls.EMAIL_REGEX.sub("[REDACTED_EMAIL]", scrubbed)
        
        token_matches = len(cls.API_KEY_REGEX.findall(scrubbed))
        scrubbed = cls.API_KEY_REGEX.sub("token=[REDACTED_TOKEN]", scrubbed)
        
        ip_matches = len(cls.IPV4_REGEX.findall(scrubbed))
        scrubbed = cls.IPV4_REGEX.sub("[REDACTED_IP]", scrubbed)
        
        cc_matches = len(cls.CREDIT_CARD_REGEX.findall(scrubbed))
        scrubbed = cls.CREDIT_CARD_REGEX.sub("[REDACTED_CC]", scrubbed)
        
        total_redacted = email_matches + token_matches + ip_matches + cc_matches
        return scrubbed, total_redacted
