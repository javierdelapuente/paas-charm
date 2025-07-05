# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for SMTP Integration."""

import json
import logging
import re
from uuid import uuid4

import pytest
import requests
from playwright.sync_api import expect, Page

logger = logging.getLogger(__name__)

import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.browser_context_args(ignore_https_errors=True)
@pytest.mark.parametrize(
    "app_fixture, port, endpoint",
    [
        ("spring_boot_app", 8080, "login"),
        # ("expressjs_app", 8080),
        # ("fastapi_app", 8080),
        # ("go_app", 8080),
        ("flask_app", 8000, "login"),
        ("django_app", 8000, "auth_login"),
    ],
)
def test_oidc_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
    port,
    endpoint,
    request: pytest.FixtureRequest,
    http: requests.Session,
    identity_bundle,
    pytestconfig: pytest.Config,
    page: Page,
):
    """
    arrange: set up the test Juju model.
    act: build and deploy the Penpot charm with required services.
    assert: the Penpot charm becomes active.
    """
    app = request.getfixturevalue(app_fixture)
    try:
        juju.integrate(f"{app.name}", "traefik-public")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    
    try:
        juju.integrate(f"{app.name}:oauth", "hydra")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    try:
        juju.integrate(f"{app.name}:receive-ca-cert", "self-signed-certificates:send-ca-cert")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(
        jubilant.all_active,
        timeout=30 * 60,
    )
    try:
        create_account_res = juju.run("kratos/0","create-admin-account", {"email":"test@example.com", "password": "Testing1", "username":"admin"})
        logger.info("JAVI create_account_res %s", create_account_res)
        logger.info("JAVI create_account_res %s", create_account_res.results)
    except jubilant.TaskError as err:
        logger.info("JAVI error create_account_res %s", err)

    # add secret password
    try:
        secret_id = juju.add_secret("user-password", {"password": "Testing1"})
        # grant secret to kratos
        juju.cli("grant-secret",secret_id, "kratos" )
        # run kratos action to reset password
        reset_password_res = juju.run("kratos/0", "reset-password", {"email": "test@example.com", "password-secret-id": secret_id.split(":")[-1]})
        logger.info("JAVI reset_password_res %s", reset_password_res)
        logger.info("JAVI reset_password_res %s", reset_password_res.results)
        # juju run kratos/0 reset-password email=test3@example.com password-secret-id=d1ifqhnmp25c77uf5gug
    except jubilant.CLIError as err:
        logger.info("JAVI error add-secret %s", err)

    res = json.loads(
        juju.run("traefik-public/0", "show-proxied-endpoints").results["proxied-endpoints"]
    )
    app_url = res[app.name]["url"]
    page.goto(f'{app_url}/{endpoint}')
    logger.info(f'GO TO: {app_url}/{endpoint}')
    # Fill an input.
    page.locator("#\\:r1\\:").fill("test@example.com")
    page.locator("#\\:r4\\:").fill("Testing1")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(re.compile(f"^{app_url}.*"))

    # Cleanup
    juju.run("kratos/0", "delete-identity", {"email": "test@example.com"})
