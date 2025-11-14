# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for paas_config module."""

import pathlib
import tempfile

import pytest
import yaml
from pydantic import ValidationError

from paas_charm.paas_config import (
    PaasCharmConfig,
    ScrapeConfig,
    StaticConfig,
    convert_to_prometheus_jobs,
    process_scheduler_placeholder,
    read_paas_charm_config,
)


class TestStaticConfig:
    """Tests for StaticConfig model."""

    def test_valid_static_config(self):
        """
        arrange: valid static config data.
        act: create StaticConfig instance.
        assert: instance is created successfully.
        """
        config = StaticConfig(targets=["*:8080"], labels={"env": "prod"})
        assert config.targets == ["*:8080"]
        assert config.labels == {"env": "prod"}

    def test_empty_targets_validation(self):
        """
        arrange: static config with empty targets list.
        act: attempt to create StaticConfig instance.
        assert: ValidationError is raised.
        """
        with pytest.raises(ValidationError, match="targets list cannot be empty"):
            StaticConfig(targets=[])

    def test_default_labels(self):
        """
        arrange: static config without labels.
        act: create StaticConfig instance.
        assert: labels default to empty dict.
        """
        config = StaticConfig(targets=["*:8080"])
        assert config.labels == {}


class TestScrapeConfig:
    """Tests for ScrapeConfig model."""

    def test_valid_scrape_config(self):
        """
        arrange: valid scrape config data.
        act: create ScrapeConfig instance.
        assert: instance is created successfully.
        """
        config = ScrapeConfig(
            job_name="my-job",
            metrics_path="/custom",
            static_configs=[StaticConfig(targets=["*:8080"])],
        )
        assert config.job_name == "my-job"
        assert config.metrics_path == "/custom"
        assert len(config.static_configs) == 1

    def test_default_metrics_path(self):
        """
        arrange: scrape config without metrics_path.
        act: create ScrapeConfig instance.
        assert: metrics_path defaults to /metrics.
        """
        config = ScrapeConfig(job_name="my-job", static_configs=[StaticConfig(targets=["*:8080"])])
        assert config.metrics_path == "/metrics"

    def test_empty_job_name_validation(self):
        """
        arrange: scrape config with empty job_name.
        act: attempt to create ScrapeConfig instance.
        assert: ValidationError is raised.
        """
        with pytest.raises(ValidationError, match="job_name cannot be empty"):
            ScrapeConfig(job_name="", static_configs=[StaticConfig(targets=["*:8080"])])

    def test_empty_static_configs_validation(self):
        """
        arrange: scrape config with empty static_configs list.
        act: attempt to create ScrapeConfig instance.
        assert: ValidationError is raised.
        """
        with pytest.raises(ValidationError, match="static_configs list cannot be empty"):
            ScrapeConfig(job_name="my-job", static_configs=[])


class TestPaasCharmConfig:
    """Tests for PaasCharmConfig model."""

    def test_valid_paas_charm_config(self):
        """
        arrange: valid paas-charm.yaml data.
        act: create PaasCharmConfig instance.
        assert: instance is created successfully.
        """
        config = PaasCharmConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="job1",
                    metrics_path="/metrics",
                    static_configs=[StaticConfig(targets=["*:8080"])],
                )
            ]
        )
        assert len(config.scrape_configs) == 1
        assert config.scrape_configs[0].job_name == "job1"

    def test_empty_scrape_configs(self):
        """
        arrange: paas-charm config without scrape_configs.
        act: create PaasCharmConfig instance.
        assert: scrape_configs defaults to empty list.
        """
        config = PaasCharmConfig()
        assert config.scrape_configs == []


class TestReadPaasCharmConfig:
    """Tests for read_paas_charm_config function."""

    def test_read_valid_config_file(self):
        """
        arrange: valid paas-charm.yaml file.
        act: read the file.
        assert: PaasCharmConfig is returned.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump(
                {
                    "scrape_configs": [
                        {
                            "job_name": "test-job",
                            "metrics_path": "/metrics",
                            "static_configs": [{"targets": ["*:8080"]}],
                        }
                    ]
                },
                tmp,
            )
            tmp_path = pathlib.Path(tmp.name)

        try:
            config = read_paas_charm_config(tmp_path)
            assert config is not None
            assert len(config.scrape_configs) == 1
            assert config.scrape_configs[0].job_name == "test-job"
        finally:
            tmp_path.unlink()

    def test_read_nonexistent_file(self):
        """
        arrange: nonexistent file path.
        act: attempt to read the file.
        assert: None is returned.
        """
        config = read_paas_charm_config(pathlib.Path("/nonexistent/file.yaml"))
        assert config is None

    def test_read_empty_file(self):
        """
        arrange: empty yaml file.
        act: read the file.
        assert: PaasCharmConfig with empty scrape_configs is returned.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("")
            tmp_path = pathlib.Path(tmp.name)

        try:
            config = read_paas_charm_config(tmp_path)
            assert config is not None
            assert config.scrape_configs == []
        finally:
            tmp_path.unlink()

    def test_read_invalid_yaml(self):
        """
        arrange: file with invalid YAML syntax.
        act: attempt to read the file.
        assert: None is returned.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("invalid: yaml: content: [[[")
            tmp_path = pathlib.Path(tmp.name)

        try:
            config = read_paas_charm_config(tmp_path)
            assert config is None
        finally:
            tmp_path.unlink()


class TestProcessSchedulerPlaceholder:
    """Tests for process_scheduler_placeholder function."""

    def test_scheduler_placeholder_on_scheduler_unit(self):
        """
        arrange: target with @scheduler placeholder on scheduler unit.
        act: process the placeholder.
        assert: @scheduler is replaced with localhost.
        """
        result = process_scheduler_placeholder("@scheduler:8081", "app/0", True)
        assert result == "localhost:8081"

    def test_scheduler_placeholder_on_non_scheduler_unit(self):
        """
        arrange: target with @scheduler placeholder on non-scheduler unit.
        act: process the placeholder.
        assert: None is returned.
        """
        result = process_scheduler_placeholder("@scheduler:8081", "app/1", False)
        assert result is None

    def test_no_placeholder(self):
        """
        arrange: target without @scheduler placeholder.
        act: process the placeholder.
        assert: target is returned unchanged.
        """
        result = process_scheduler_placeholder("*:8080", "app/0", True)
        assert result == "*:8080"

    def test_wildcard_preserved(self):
        """
        arrange: target with wildcard.
        act: process the placeholder.
        assert: wildcard is preserved.
        """
        result = process_scheduler_placeholder("*:8080", "app/1", False)
        assert result == "*:8080"


class TestConvertToPrometheusJobs:
    """Tests for convert_to_prometheus_jobs function."""

    def test_convert_single_job(self):
        """
        arrange: config with single job.
        act: convert to prometheus jobs.
        assert: correct job structure is returned.
        """
        config = PaasCharmConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="test-job",
                    metrics_path="/metrics",
                    static_configs=[StaticConfig(targets=["*:8080"])],
                )
            ]
        )
        jobs = convert_to_prometheus_jobs(config, "app/0", False)
        assert len(jobs) == 1
        assert jobs[0]["metrics_path"] == "/metrics"
        assert jobs[0]["static_configs"][0]["targets"] == ["*:8080"]
        assert jobs[0]["job_name"] == "test-job"

    def test_convert_job_with_labels(self):
        """
        arrange: config with labels.
        act: convert to prometheus jobs.
        assert: labels are included in output.
        """
        config = PaasCharmConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="test-job",
                    static_configs=[
                        StaticConfig(targets=["*:8080"], labels={"env": "prod", "team": "ops"})
                    ],
                )
            ]
        )
        jobs = convert_to_prometheus_jobs(config, "app/0", False)
        assert len(jobs) == 1
        assert jobs[0]["static_configs"][0]["labels"] == {"env": "prod", "team": "ops"}

    def test_convert_with_scheduler_placeholder(self):
        """
        arrange: config with @scheduler placeholder on scheduler unit.
        act: convert to prometheus jobs.
        assert: @scheduler is replaced with localhost.
        """
        config = PaasCharmConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="scheduler-job",
                    static_configs=[StaticConfig(targets=["@scheduler:8081"])],
                )
            ]
        )
        jobs = convert_to_prometheus_jobs(config, "app/0", True)
        assert len(jobs) == 1
        assert jobs[0]["static_configs"][0]["targets"] == ["localhost:8081"]

    def test_convert_filters_scheduler_on_non_scheduler_unit(self):
        """
        arrange: config with @scheduler placeholder on non-scheduler unit.
        act: convert to prometheus jobs.
        assert: scheduler job is filtered out.
        """
        config = PaasCharmConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="scheduler-job",
                    static_configs=[StaticConfig(targets=["@scheduler:8081"])],
                ),
                ScrapeConfig(
                    job_name="regular-job", static_configs=[StaticConfig(targets=["*:8080"])]
                ),
            ]
        )
        jobs = convert_to_prometheus_jobs(config, "app/1", False)
        # Only regular-job should remain
        assert len(jobs) == 1
        assert jobs[0]["job_name"] == "regular-job"

    def test_convert_multiple_targets_in_static_config(self):
        """
        arrange: config with multiple targets in one static_config.
        act: convert to prometheus jobs.
        assert: all targets are included.
        """
        config = PaasCharmConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="multi-target",
                    static_configs=[StaticConfig(targets=["*:8080", "*:8081", "*:8082"])],
                )
            ]
        )
        jobs = convert_to_prometheus_jobs(config, "app/0", False)
        assert len(jobs) == 1
        assert jobs[0]["static_configs"][0]["targets"] == ["*:8080", "*:8081", "*:8082"]

    def test_convert_mixed_targets_with_scheduler(self):
        """
        arrange: config with both wildcard and scheduler targets on scheduler unit.
        act: convert to prometheus jobs.
        assert: both targets are processed correctly.
        """
        config = PaasCharmConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="mixed-job",
                    static_configs=[StaticConfig(targets=["*:8080", "@scheduler:8081"])],
                )
            ]
        )
        jobs = convert_to_prometheus_jobs(config, "app/0", True)
        assert len(jobs) == 1
        assert jobs[0]["static_configs"][0]["targets"] == ["*:8080", "localhost:8081"]

    def test_convert_empty_config(self):
        """
        arrange: config with no scrape_configs.
        act: convert to prometheus jobs.
        assert: empty list is returned.
        """
        config = PaasCharmConfig()
        jobs = convert_to_prometheus_jobs(config, "app/0", False)
        assert jobs == []
