.. _ref_supported_customization:

Supported customizable features and capabilities
================================================

The following features and capabilities are customizable
in a 12-factor app rock and charm:

* `Adding configurations <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/configure-web-app-charm/#add-a-new-configuration>`_
* `Adding actions <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/configure-web-app-charm/#add-a-custom-action>`_
* `Adding new dependencies in the OCI image <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/web-app-rocks/set-up-web-app-rock/#include-additional-debs-in-the-oci-image>`_
* `Adding extra files or changing the project structure <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/web-app-rocks/set-up-web-app-rock/#include-extra-files-in-the-oci-image>`_
* `Database migrations <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/use-web-app-charm/#migrate-the-workload-database>`_
* `Enabling supported relations <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/integrate-web-app-charm/>`_
* `Handling secrets <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/configure-web-app-charm/#manage-secrets>`_
* Overriding commands
* :ref:`Custom Prometheus metrics <ref_custom_prometheus_metrics>`
* Task manager and scheduler
    .. tabs::

        .. group-tab:: Django

            `Charmcraft Django extension | Worker and Scheduler Services <https://documentation.ubuntu.com/charmcraft/latest/reference/extensions/django-framework-extension/#worker-and-scheduler-services>`_

        .. group-tab:: Express

            `Charmcraft Express extension | Worker and Scheduler Services <https://documentation.ubuntu.com/charmcraft/latest/reference/extensions/express-framework-extension/#worker-and-scheduler-services>`_

        .. group-tab:: FastAPI

            `Charmcraft FastAPI extension | Worker and Scheduler Services <https://documentation.ubuntu.com/charmcraft/latest/reference/extensions/fastapi-framework-extension/#worker-and-scheduler-services>`_

        .. group-tab:: Flask

            `Charmcraft Flask extension | Worker and Scheduler Services <https://documentation.ubuntu.com/charmcraft/latest/reference/extensions/flask-framework-extension/#worker-and-scheduler-services>`_

        .. group-tab:: Go

            `Charmcraft Go extension | Worker and Scheduler Services <https://documentation.ubuntu.com/charmcraft/latest/reference/extensions/go-framework-extension/#worker-and-scheduler-services>`_

        .. group-tab:: Spring Boot

            `Charmcraft Spring Boot extension | Worker and Scheduler Services <https://documentation.ubuntu.com/charmcraft/latest/reference/extensions/spring-boot-framework-extension/#worker-and-scheduler-services>`_

.. _ref_custom_prometheus_metrics:

Custom Prometheus Metrics
--------------------------

You can configure custom Prometheus metrics scraping by creating a ``paas-charm.yaml`` file in your application directory (the same directory where migration scripts are placed). This file allows you to define multiple scrape targets using Prometheus file-based service discovery format.

File Location
~~~~~~~~~~~~~

Place the ``paas-charm.yaml`` file in your application's root directory. This is typically:

* Django: ``/django/app``
* Flask: ``/flask/app``
* FastAPI: ``/app``
* Express.js: ``/app``
* Go: ``/app``
* Spring Boot: ``/app``

File Format
~~~~~~~~~~~

The ``paas-charm.yaml`` file uses the following structure:

.. code-block:: yaml

    scrape_configs:
      - job_name: <string>
        metrics_path: <path>  # Optional, defaults to /metrics
        static_configs:
          - targets:
              - <host>
              - ...
            labels:
              <labelname>: <labelvalue>
              ...

Target Syntax
~~~~~~~~~~~~~

Targets can use the following formats:

* **Standard format**: ``hostname:port`` or ``IP:port`` (e.g., ``myapp:8080``)
* **Wildcard**: ``*:port`` - Scrapes all units in the application (e.g., ``*:8080``)
* **Scheduler placeholder**: ``@scheduler:port`` - Only scrapes the unit running scheduler services (unit/0)

The ``@scheduler`` placeholder is automatically replaced with ``localhost`` on unit/0 and filtered out on other units.

Example Configuration
~~~~~~~~~~~~~~~~~~~~~

Here's an example ``paas-charm.yaml`` that exposes multiple metrics endpoints:

.. code-block:: yaml

    scrape_configs:
      # Main application metrics on all units
      - job_name: "app-main"
        metrics_path: "/metrics"
        static_configs:
          - targets:
              - "*:8080"
            labels:
              tier: "main"
      
      # Admin metrics on all units
      - job_name: "app-admin"
        metrics_path: "/admin/metrics"
        static_configs:
          - targets:
              - "*:8080"
            labels:
              tier: "admin"
      
      # Scheduler-specific metrics (only on unit/0)
      - job_name: "app-scheduler"
        metrics_path: "/scheduler/metrics"
        static_configs:
          - targets:
              - "@scheduler:8081"
            labels:
              tier: "scheduler"

Backward Compatibility
~~~~~~~~~~~~~~~~~~~~~~

The ``paas-charm.yaml`` configuration is optional and works alongside existing ``metrics_port`` and ``metrics_path`` charm configuration options. If both are present, all scrape targets will be combined.

Framework-Specific Notes
~~~~~~~~~~~~~~~~~~~~~~~~

**Django and Flask (Gunicorn-based)**

By default, these frameworks expose a StatsD exporter on port 9102. You can add custom application metrics endpoints via ``paas-charm.yaml``:

.. code-block:: yaml

    scrape_configs:
      - job_name: "django-app"
        metrics_path: "/custom/metrics"
        static_configs:
          - targets:
              - "*:8000"

**FastAPI, Go, Express.js, Spring Boot**

These frameworks can expose metrics on their main application port or custom ports:

.. code-block:: yaml

    scrape_configs:
      - job_name: "fastapi-app"
        metrics_path: "/metrics"
        static_configs:
          - targets:
              - "*:8000"

**Worker and Scheduler Services**

If your application has worker or scheduler services that expose metrics, use the ``@scheduler`` placeholder for scheduler-specific endpoints:

.. code-block:: yaml

    scrape_configs:
      - job_name: "celery-worker"
        metrics_path: "/worker/metrics"
        static_configs:
          - targets:
              - "*:9091"
      
      - job_name: "celery-beat"
        metrics_path: "/beat/metrics"
        static_configs:
          - targets:
              - "@scheduler:9092"

Validation
~~~~~~~~~~

The charm validates the ``paas-charm.yaml`` file on startup and logs warnings if:

* The file has invalid YAML syntax
* Required fields are missing
* Field values don't meet validation requirements

If validation fails, the charm will continue to operate but won't configure the custom scrape targets.

