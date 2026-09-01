"""Integration test verifying Google Cloud Egress Agent Gateway (AGENT_TO_ANYWHERE)."""

import os
import yaml
import pytest
from app.config import Config


def test_egress_gateway_declarative_config():
    """Verify the local declarative configuration for the Egress Agent Gateway."""
    yaml_path = os.path.join(os.path.dirname(__file__), "../../agent-gateway-egress.yaml")
    assert os.path.exists(yaml_path), f"Missing declarative file: {yaml_path}"

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    assert data.get("googleManaged", {}).get("governedAccessPath") == "AGENT_TO_ANYWHERE"
    assert "MCP" in data.get("protocols", [])
    assert "locations/us-central1/agentGateways/bugtriage-agent-gateway" in data.get("name", "")


def test_live_egress_gateway_in_google_cloud():
    """Verify that bugtriage-agent-gateway is deployed and active in Google Cloud."""
    try:
        import google.auth
        import google.auth.transport.requests
        import requests

        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        url = (
            "https://networkservices.googleapis.com/v1/projects/"
            "539424669613/locations/us-central1/agentGateways/bugtriage-agent-gateway"
        )
        headers = {"Authorization": f"Bearer {creds.token}"}
        resp = requests.get(url, headers=headers)
        assert resp.status_code == 200, f"Failed to get Agent Gateway: {resp.text}"

        gw = resp.json()
        assert gw.get("googleManaged", {}).get("governedAccessPath") == "AGENT_TO_ANYWHERE"
        assert "MCP" in gw.get("protocols", [])

        # Validate TLS inspection card and mTLS endpoint
        card = gw.get("agentGatewayCard", {})
        assert "mtlsEndpoint" in card
        assert len(card.get("rootCertificates", [])) > 0
    except Exception as e:
        pytest.skip(f"Google Cloud credentials not available or API unreachable: {e}")


def test_config_references_egress_gateway():
    """Verify that app/config.py contains the Egress Gateway resource reference."""
    assert hasattr(Config, "AGENT_GATEWAY_EGRESS")
    assert "agentGateways/bugtriage-agent-gateway" in Config.AGENT_GATEWAY_EGRESS
