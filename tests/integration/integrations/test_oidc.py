# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for SMTP Integration."""

import logging
import re

import pytest
import requests
from oauth_tools.oauth_helpers import (
    access_application_login_page,
    click_on_sign_in_button_by_text,
)
from playwright.async_api import expect

logger = logging.getLogger(__name__)

pytest_plugins = ["oauth_tools.fixtures"]
import logging

import jubilant
import pytest
import requests
from oauth_tools.oauth_helpers import (
    access_application_login_page,
    click_on_sign_in_button_by_text,
)

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("spring_boot_app", 8080),
        ("expressjs_app", 8080),
        ("fastapi_app", 8080),
        ("go_app", 8080),
        ("flask_app", 8000),
        ("django_app", 8000),
    ],
)
async def test_oidc_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
    port,
    request: pytest.FixtureRequest,
    mailcatcher,
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
    juju.integrate(f"{app.name}:oauth", "hydra")
    juju.wait(
        jubilant.all_active,
        timeout=30 * 60,
    )
    await access_application_login_page(page=page, url="https://penpot.local/#/auth/login")
    await click_on_sign_in_button_by_text(page=page, text="OpenID")
    # await complete_auth_code_login(page=page, ops_test=ops_test, ext_idp_service=ext_idp_service)
    await expect(page).to_have_url(re.compile("^https://penpot\\.local/#/auth/register.*"))

