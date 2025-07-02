# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm service."""
import logging

import ops
from charms.certificate_transfer_interface.v0.certificate_transfer import (
    CertificateAvailableEvent,
    CertificateRemovedEvent,
    CertificateTransferRequires,
)
from pydantic import ConfigDict, Field, field_validator

from paas_charm._gunicorn.charm import GunicornBase
from paas_charm.framework import FrameworkConfig

logger = logging.getLogger(__name__)


class FlaskConfig(FrameworkConfig):
    """Represent Flask builtin configuration values.

    Attrs:
        env: what environment the Flask app is running in, by default it's 'production'.
        debug: whether Flask debug mode is enabled.
        secret_key: a secret key that will be used for securely signing the session cookie
            and can be used for any other security related needs by your Flask application.
        permanent_session_lifetime: set the cookie’s expiration to this number of seconds in the
            Flask application permanent sessions.
        application_root: inform the Flask application what path it is mounted under by the
            application / web server.
        session_cookie_secure: set the secure attribute in the Flask application cookies.
        preferred_url_scheme: use this scheme for generating external URLs when not in a request
            context in the Flask application.
        model_config: Pydantic model configuration.
    """

    env: str | None = Field(alias="flask-env", default=None, min_length=1)
    debug: bool | None = Field(alias="flask-debug", default=None)
    secret_key: str | None = Field(alias="flask-secret-key", default=None, min_length=1)
    permanent_session_lifetime: int | None = Field(
        alias="flask-permanent-session-lifetime", default=None, gt=0
    )
    application_root: str | None = Field(
        alias="flask-application-root", default=None, min_length=1
    )
    session_cookie_secure: bool | None = Field(alias="flask-session-cookie-secure", default=None)
    preferred_url_scheme: str | None = Field(
        alias="flask-preferred-url-scheme", default=None, pattern="(?i)^(HTTP|HTTPS)$"
    )
    model_config = ConfigDict(extra="ignore")

    @field_validator("preferred_url_scheme")
    @staticmethod
    def to_upper(value: str) -> str:
        """Convert the string field to uppercase.

        Args:
            value: the input value.

        Returns:
            The string converted to uppercase.
        """
        return value.upper()


class Charm(GunicornBase):
    """Flask Charm service.

    Attrs:
        framework_config_class: Base class for framework configuration.
    """

    framework_config_class = FlaskConfig

    def __init__(self, framework: ops.Framework) -> None:
        """Initialize the Flask charm.

        Args:
            framework: operator framework.
        """
        super().__init__(framework=framework, framework_name="flask")
        self.trusted_cert_transfer = CertificateTransferRequires(self, "receive-ca-cert")
        self.framework.observe(
            self.trusted_cert_transfer.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self.trusted_cert_transfer.on.certificate_removed, self._on_certificate_removed
        )
        rel_name = self.trusted_cert_transfer.relationship_name
        _cert_relation = self.model.get_relation(relation_name=rel_name)
        try:
            if self.trusted_cert_transfer.is_ready(_cert_relation):
                for relation in self.model.relations.get(rel_name, []):
                    # For some reason, relation.units includes our unit and app. Need to exclude them.
                    for unit in set(relation.units).difference([self.app, self.unit]):
                        # Note: this nested loop handles the case of multi-unit CA, each unit providing
                        # a different ca cert, but that is not currently supported by the lib itself.
                        if cert := relation.data[unit].get("ca"):
                            self._container.push("/flask/app/ca.crt", cert)
        except:
            logger.warning("TLS RELATION EMPTY?")


    def _on_certificate_available(self, event: CertificateAvailableEvent):
        logger.warning(f"{event.certificate=}")
        logger.warning(f"{event.ca=}")
        self._container.push("/flask/app/ca.crt", event.ca)

    def _on_certificate_removed(self, event: CertificateRemovedEvent):
        logger.warning(event.relation_id)
