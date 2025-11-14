# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for parsing and processing paas-charm.yaml configuration file."""
import logging
import pathlib
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class StaticConfig(BaseModel):
    """Represents a static_config section in prometheus scrape configuration.

    Attributes:
        targets: List of target hosts to scrape (supports wildcards like * and @scheduler).
        labels: Optional labels to apply to scraped metrics.
    """

    targets: list[str]
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("targets")
    @classmethod
    def validate_targets(cls, targets: list[str]) -> list[str]:
        """Validate that targets list is not empty.

        Args:
            targets: List of target strings.

        Returns:
            The validated targets list.

        Raises:
            ValueError: If targets list is empty.
        """
        if not targets:
            raise ValueError("targets list cannot be empty")
        return targets


class ScrapeConfig(BaseModel):
    """Represents a scrape_config section in prometheus configuration.

    Attributes:
        job_name: The job name assigned to scraped metrics.
        metrics_path: The HTTP resource path on which to fetch metrics (default: /metrics).
        static_configs: List of static configurations for this job.
    """

    job_name: str
    metrics_path: str = "/metrics"
    static_configs: list[StaticConfig]

    @field_validator("job_name")
    @classmethod
    def validate_job_name(cls, job_name: str) -> str:
        """Validate that job_name is not empty.

        Args:
            job_name: The job name string.

        Returns:
            The validated job name.

        Raises:
            ValueError: If job_name is empty.
        """
        if not job_name or not job_name.strip():
            raise ValueError("job_name cannot be empty")
        return job_name

    @field_validator("static_configs")
    @classmethod
    def validate_static_configs(cls, static_configs: list[StaticConfig]) -> list[StaticConfig]:
        """Validate that static_configs list is not empty.

        Args:
            static_configs: List of static configurations.

        Returns:
            The validated static_configs list.

        Raises:
            ValueError: If static_configs list is empty.
        """
        if not static_configs:
            raise ValueError("static_configs list cannot be empty")
        return static_configs


class PaasCharmConfig(BaseModel):
    """Represents the paas-charm.yaml configuration file.

    Attributes:
        scrape_configs: List of prometheus scrape configurations.
    """

    scrape_configs: list[ScrapeConfig] = Field(default_factory=list)


def read_paas_charm_config(config_path: pathlib.Path) -> PaasCharmConfig | None:
    """Read and parse paas-charm.yaml configuration file.

    Args:
        config_path: Path to the paas-charm.yaml file.

    Returns:
        PaasCharmConfig object if file exists and is valid, None otherwise.
    """
    if not config_path.exists():
        logger.debug("paas-charm.yaml not found at %s", config_path)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            yaml_content = yaml.safe_load(file)

        if yaml_content is None:
            logger.warning("paas-charm.yaml at %s is empty", config_path)
            return PaasCharmConfig()

        config = PaasCharmConfig(**yaml_content)
        logger.info(
            "Successfully loaded paas-charm.yaml with %d scrape configs",
            len(config.scrape_configs),
        )
        return config

    except yaml.YAMLError as exc:
        logger.error("Failed to parse paas-charm.yaml at %s: %s", config_path, exc)
        return None
    except Exception as exc:
        logger.error("Failed to read paas-charm.yaml at %s: %s", config_path, exc)
        return None


def process_scheduler_placeholder(
    target: str, unit_name: str, should_run_scheduler: bool
) -> str | None:
    """Process @scheduler placeholder in target string.

    Args:
        target: Target string that may contain @scheduler placeholder.
        unit_name: Name of the current unit.
        should_run_scheduler: Whether this unit should run scheduler processes.

    Returns:
        The processed target string, or None if @scheduler is used but this unit
        should not run schedulers.
    """
    if "@scheduler" in target:
        if should_run_scheduler:
            # Replace @scheduler with localhost since scheduler runs on this unit
            return target.replace("@scheduler", "localhost")
        else:
            # This unit should not expose scheduler metrics
            return None
    return target


def convert_to_prometheus_jobs(
    config: PaasCharmConfig, unit_name: str, should_run_scheduler: bool
) -> list[dict[str, Any]]:
    """Convert PaasCharmConfig to Prometheus MetricsEndpointProvider jobs format.

    Args:
        config: The parsed paas-charm.yaml configuration.
        unit_name: Name of the current unit.
        should_run_scheduler: Whether this unit should run scheduler processes.

    Returns:
        List of job dictionaries suitable for MetricsEndpointProvider.
    """
    jobs = []

    for scrape_config in config.scrape_configs:
        for static_config in scrape_config.static_configs:
            processed_targets = []
            for target in static_config.targets:
                processed_target = process_scheduler_placeholder(
                    target, unit_name, should_run_scheduler
                )
                if processed_target is not None:
                    processed_targets.append(processed_target)

            if processed_targets:
                static_config_dict: dict[str, Any] = {"targets": processed_targets}
                if static_config.labels:
                    static_config_dict["labels"] = static_config.labels
                
                job: dict[str, Any] = {
                    "metrics_path": scrape_config.metrics_path,
                    "static_configs": [static_config_dict],
                }
                # Add job_name if it's non-default
                if scrape_config.job_name:
                    job["job_name"] = scrape_config.job_name

                jobs.append(job)

    return jobs
