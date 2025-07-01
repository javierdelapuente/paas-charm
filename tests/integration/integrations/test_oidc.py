# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for SMTP Integration."""

import json
import logging
import re

import pytest
import requests
from oauth_tools.oauth_helpers import access_application_login_page
from playwright.async_api import expect

logger = logging.getLogger(__name__)

pytest_plugins = ["oauth_tools.fixtures"]
import logging

import jubilant
import pytest
import requests
from oauth_tools.oauth_helpers import access_application_login_page

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        # ("spring_boot_app", 8080),
        # ("expressjs_app", 8080),
        # ("fastapi_app", 8080),
        # ("go_app", 8080),
        ("flask_app", 8000),
        # ("django_app", 8000),
    ],
)
async def test_oidc_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
    port,
    request: pytest.FixtureRequest,
    http: requests.Session,
    ext_idp_service,
    identity_bundle,
    pytestconfig: pytest.Config,
    page,
):
    """
    arrange: set up the test Juju model.
    act: build and deploy the Penpot charm with required services.
    assert: the Penpot charm becomes active.
    """
    app = request.getfixturevalue(app_fixture)
    juju.integrate(f"{app.name}", "traefik-public")
    juju.integrate(f"{app.name}:oauth", "hydra")
    juju.integrate(f"{app.name}:receive-ca-cert", "self-signed-certificates:send-ca-cert")
    juju.wait(
        jubilant.all_active,
        timeout=30 * 60,
    )
    res = json.loads(juju.run("traefik-public/0","show-proxied-endpoints").results["proxied-endpoints"])
    app_url = res["flask-k8s"]["url"]
    await access_application_login_page(page=page, url=f"{app_url}/login")
    app_url = res["identity-platform-login-ui-operator"]["url"]
    await expect(page).to_have_url(re.compile(f"^{app_url}.*"))

