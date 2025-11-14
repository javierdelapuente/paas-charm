# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the Observability class to represent the observability stack for charms."""
import logging
import os.path
import pathlib
from typing import TYPE_CHECKING

import ops
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider

from paas_charm.paas_config import convert_to_prometheus_jobs, read_paas_charm_config
from paas_charm.utils import enable_pebble_log_forwarding

if TYPE_CHECKING:
    from paas_charm.app import WorkloadConfig

logger = logging.getLogger(__name__)


class Observability(ops.Object):
    """A class representing the observability stack for charm managed application."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        charm: ops.CharmBase,
        container_name: str,
        cos_dir: str,
        log_files: list[pathlib.Path],
        metrics_target: str | None,
        metrics_path: str | None,
        workload_config: "WorkloadConfig | None" = None,
        container: "ops.Container | None" = None,
    ):
        """Initialize a new instance of the Observability class.

        Args:
            charm: The charm object that the Observability instance belongs to.
            container_name: The name of the application container.
            cos_dir: The directories containing the grafana_dashboards, loki_alert_rules and
                prometheus_alert_rules.
            log_files: List of files to monitor.
            metrics_target: Target to scrape for metrics.
            metrics_path: Path to scrape for metrics.
            workload_config: Optional workload configuration for reading paas-charm.yaml.
            container: Optional container for checking paas-charm.yaml file existence.
        """
        super().__init__(charm, "observability")
        self._charm = charm
        jobs = self._build_prometheus_jobs(
            metrics_target, metrics_path, workload_config, container
        )
        self._metrics_endpoint = MetricsEndpointProvider(
            charm,
            alert_rules_path=os.path.join(cos_dir, "prometheus_alert_rules"),
            jobs=jobs,
            relation_name="metrics-endpoint",
            refresh_event=[charm.on.config_changed, charm.on[container_name].pebble_ready],
        )
        # The charm isn't necessarily bundled with charms.loki_k8s.v1
        # Dynamically switches between two versions here.
        if enable_pebble_log_forwarding():
            # ignore "import outside toplevel" linting error
            import charms.loki_k8s.v1.loki_push_api  # pylint: disable=import-outside-toplevel

            self._logging = charms.loki_k8s.v1.loki_push_api.LogForwarder(
                charm, relation_name="logging"
            )
        else:
            try:
                # ignore "import outside toplevel" linting error
                import charms.loki_k8s.v0.loki_push_api  # pylint: disable=import-outside-toplevel

                self._logging = charms.loki_k8s.v0.loki_push_api.LogProxyConsumer(
                    charm,
                    alert_rules_path=os.path.join(cos_dir, "loki_alert_rules"),
                    container_name=container_name,
                    log_files=[str(log_file) for log_file in log_files],
                    relation_name="logging",
                )
            except ImportError:
                # ignore "import outside toplevel" linting error
                import charms.loki_k8s.v1.loki_push_api  # pylint: disable=import-outside-toplevel

                self._logging = charms.loki_k8s.v1.loki_push_api.LogProxyConsumer(
                    charm,
                    logs_scheme={
                        container_name: {
                            "log-files": [str(log_file) for log_file in log_files],
                        },
                    },
                    relation_name="logging",
                )

        self._grafana_dashboards = GrafanaDashboardProvider(
            charm,
            dashboards_path=os.path.join(cos_dir, "grafana_dashboards"),
            relation_name="grafana-dashboard",
        )

    def _build_prometheus_jobs(
        self,
        metrics_target: str | None,
        metrics_path: str | None,
        workload_config: "WorkloadConfig | None",
        container: "ops.Container | None",
    ) -> list[dict] | None:
        """Build Prometheus jobs from paas-charm.yaml and legacy config options.

        Args:
            metrics_target: Legacy target to scrape for metrics.
            metrics_path: Legacy path to scrape for metrics.
            workload_config: Workload configuration containing app_dir and unit info.
            container: Container to check for paas-charm.yaml file existence.

        Returns:
            List of Prometheus job configurations, or None if no jobs configured.
        """
        jobs = []

        # Try to read paas-charm.yaml if workload_config and container are provided
        if workload_config is not None and container is not None:
            paas_config_path = workload_config.app_dir / "paas-charm.yaml"

            # Only try to read if the container can access the file
            if container.can_connect():
                try:
                    if container.exists(paas_config_path):
                        # Read the file from container
                        config_content = container.pull(paas_config_path).read()
                        # Write to a temporary location for parsing
                        import tempfile

                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=".yaml", delete=False
                        ) as tmp_file:
                            tmp_file.write(config_content)
                            tmp_path = pathlib.Path(tmp_file.name)

                        try:
                            paas_config = read_paas_charm_config(tmp_path)
                            if paas_config is not None:
                                custom_jobs = convert_to_prometheus_jobs(
                                    paas_config,
                                    workload_config.unit_name,
                                    workload_config.should_run_scheduler(),
                                )
                                jobs.extend(custom_jobs)
                                logger.info(
                                    "Loaded %d custom Prometheus jobs from paas-charm.yaml",
                                    len(custom_jobs),
                                )
                        finally:
                            # Clean up temporary file
                            import os

                            os.unlink(tmp_path)
                except Exception as exc:
                    logger.warning(
                        "Failed to read paas-charm.yaml from %s: %s", paas_config_path, exc
                    )

        # Add legacy metrics_target/metrics_path if provided
        if metrics_path and metrics_target:
            legacy_job = {
                "metrics_path": metrics_path,
                "static_configs": [{"targets": [metrics_target]}],
            }
            jobs.append(legacy_job)
            logger.debug("Added legacy metrics job: %s", legacy_job)

        return jobs if jobs else None
