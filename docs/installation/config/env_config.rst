.. _installation_env_config:

===================================
Environment configuration reference
===================================


Open Zaak can be ran both as a Docker container or directly on a VPS or
dedicated server. It relies on other services, such as database and cache
backends, which can be configured through environment variables.


Available environment variables
===============================


Required
--------

* ``SECRET_KEY``: Secret key that's used for certain cryptographic utilities. You should generate one via `miniwebtool <https://www.miniwebtool.com/django-secret-key-generator>`_.
* ``ALLOWED_HOSTS``: a comma separated (without spaces!) list of domains that serve the installation. Used to protect against Host header attacks. Defaults to: ``(empty string)``.


Database
--------

* ``DB_NAME``: name of the PostgreSQL database. Defaults to: ``openzaak``.
* ``DB_USER``: username of the database user. Defaults to: ``openzaak``.
* ``DB_PASSWORD``: password of the database user. Defaults to: ``openzaak``.
* ``DB_HOST``: hostname of the PostgreSQL database. Defaults to ``db`` for the docker environment, otherwise defaults to ``localhost``.
* ``DB_PORT``: port number of the database. Defaults to: ``5432``.


Cross-Origin-Resource-Sharing
-----------------------------

* ``CORS_ALLOW_ALL_ORIGINS``: allow cross-domain access from any client. Defaults to: ``False``.
* ``CORS_ALLOWED_ORIGINS``: explicitly list the allowed origins for cross-domain requests. Example: http://localhost:3000,https://some-app.gemeente.nl. Defaults to: ``[]``.
* ``CORS_ALLOWED_ORIGIN_REGEXES``: same as ``CORS_ALLOWED_ORIGINS``, but supports regular expressions. Defaults to: ``[]``.
* ``CORS_EXTRA_ALLOW_HEADERS``: headers that are allowed to be sent as part of the cross-domain request. By default, Authorization, Accept-Crs and Content-Crs are already included. The value of this variable is added to these already included headers. Defaults to: ``[]``.


Celery
------

* ``CELERY_RESULT_BACKEND``: the URL of the backend/broker that will be used by Celery to send the notifications. Defaults to: ``redis://localhost:6379/1``.


Elastic APM
-----------

* ``ELASTIC_APM_SERVER_URL``: URL where Elastic APM is hosted. Defaults to: ``None``.
* ``ELASTIC_APM_SERVICE_NAME``: Name of the service for this application in Elastic APM. Defaults to ``openzaak - <environment>``.
* ``ELASTIC_APM_SECRET_TOKEN``: Token used to communicate with Elastic APM. Defaults to: ``default``.
* ``ELASTIC_APM_TRANSACTION_SAMPLE_RATE``: By default, the agent will sample every transaction (e.g. request to your service). To reduce overhead and storage requirements, set the sample rate to a value between 0.0 and 1.0. Defaults to: ``0.1``.


Optional
--------

* ``SITE_ID``: The database ID of the site object. You usually won't have to touch this. Defaults to: ``1``.
* ``DEBUG``: Only set this to ``True`` on a local development environment. Various other security settings are derived from this setting!. Defaults to: ``False``.
* ``USE_X_FORWARDED_HOST``: whether to grab the domain/host from the X-Forwarded-Host header or not. This header is typically set by reverse proxies (such as nginx, traefik, Apache...). Note: this is a header that can be spoofed and you need to ensure you control it before enabling this. Defaults to: ``False``.
* ``IS_HTTPS``: Used to construct absolute URLs and controls a variety of security settings. Defaults to the inverse of ``DEBUG``.
* ``CACHE_DEFAULT``: redis cache address for the default cache. Defaults to: ``localhost:6379/0``.
* ``CACHE_AXES``: redis cache address for the brute force login protection cache. Defaults to: ``localhost:6379/0``.
* ``EMAIL_HOST``: hostname for the outgoing e-mail server. Defaults to: ``localhost``.
* ``EMAIL_PORT``: port number of the outgoing e-mail server. Note that if you're on Google Cloud, sending e-mail via port 25 is completely blocked and you should use 487 for TLS. Defaults to: ``25``.
* ``EMAIL_HOST_USER``: username to connect to the mail server. Defaults to: ``(empty string)``.
* ``EMAIL_HOST_PASSWORD``: password to connect to the mail server. Defaults to: ``(empty string)``.
* ``EMAIL_USE_TLS``: whether to use TLS or not to connect to the mail server. Should be True if you're changing the ``EMAIL_PORT`` to 487. Defaults to: ``False``.
* ``DEFAULT_FROM_EMAIL``: The default email address from which emails are sent. Defaults to: ``openzaak@example.com``.
* ``LOG_STDOUT``: whether to log to stdout or not. Defaults to: ``False``.
* ``LOG_LEVEL``: control the verbosity of logging output. Available values are ``CRITICAL``, ``ERROR``, ``WARNING``, ``INFO`` and ``DEBUG``. Defaults to: ``WARNING``.
* ``LOG_QUERIES``: enable (query) logging at the database backend level. Note that you must also set ``DEBUG=1``, which should be done very sparingly!. Defaults to: ``False``.
* ``LOG_REQUESTS``: enable logging of the outgoing requests. Defaults to: ``False``.
* ``ENVIRONMENT``: An identifier for the environment, displayed in the admin depending on the settings module used and included in the error monitoring (see ``SENTRY_DSN``). The default is set according to ``DJANGO_SETTINGS_MODULE``.
* ``SUBPATH``: If hosted on a subpath, provide the value here. If you provide ``/gateway``, the component assumes its running at the base URL: ``https://somedomain/gateway/``. Defaults to an empty string. Defaults to: ``None``.
* ``RELEASE``: The version number or commit hash of the application (this is also sent to Sentry).
* ``NUM_PROXIES``: the number of reverse proxies in front of the application, as an integer. This is used to determine the actual client IP adres. On Kubernetes with an ingress you typically want to set this to 2. Defaults to: ``1``.
* ``CSRF_TRUSTED_ORIGINS``: A list of trusted origins for unsafe requests (e.g. POST). Defaults to: ``[]``.
* ``NOTIFICATIONS_DISABLED``: indicates whether or not notifications should be sent to the Notificaties API for operations on the API endpoints. Defaults to ``True`` for the ``dev`` environment, otherwise defaults to ``False``.
* ``DISABLE_2FA``: Whether or not two factor authentication should be disabled. Defaults to: ``False``.
* ``LOG_OUTGOING_REQUESTS_EMIT_BODY``: Whether or not outgoing request bodies should be logged. Defaults to: ``True``.
* ``LOG_OUTGOING_REQUESTS_DB_SAVE``: Whether or not outgoing request logs should be saved to the database. Defaults to: ``False``.
* ``LOG_OUTGOING_REQUESTS_DB_SAVE_BODY``: Whether or not outgoing request bodies should be saved to the database. Defaults to: ``True``.
* ``LOG_OUTGOING_REQUESTS_MAX_AGE``: The amount of time after which request logs should be deleted from the database. Defaults to: ``7``.
* ``SENTRY_DSN``: URL of the sentry project to send error reports to. Default empty, i.e. -> no monitoring set up. Highly recommended to configure this.
* ``GEOS_LIBRARY_PATH``: Full path to the GEOS library used by GeoDjango. In most circumstances, this can be left empty. Defaults to: ``None``.
* ``GDAL_LIBRARY_PATH``: Full path to the GDAL library used by GeoDjango. In most circumstances, this can be left empty. Defaults to: ``None``.
* ``OPENZAAK_DOMAIN``: a [host]:[port] or [host] value indicating the canonical domain where Open Zaak is hosted/deployed, e.g. openzaak.example.com:8443. This value is used (together with IS_HTTPS) when fully qualified URLs need to be constructed without HTTP request context available.
* ``OPENZAAK_REWRITE_HOST``: whether to rewrite the request host of all incoming requests with the value of OPENZAAK_DOMAIN, discarding the original Host header or headers set by reverse proxies. Useful if you provide the services only via the NLX network, for example. Defaults to False and conflicts with ``USE_X_FORWARDED_HOST``.
* ``MIN_UPLOAD_SIZE``: the max allowed size of POST bodies, in bytes. Defaults to 4GiB. Note that you should also configure your web server to allow this. Defaults to: ``4294967296``.
* ``DOCUMENTEN_UPLOAD_CHUNK_SIZE``: chunk size in bytes for large file uploads - determines the size for a single upload chunk. Note that making this larger than ``MIN_UPLOAD_SIZE`` breaks large file uploads. Defaults to: ``4294967296``.
* ``DOCUMENTEN_UPLOAD_READ_CHUNK``: chunk size in bytes for large file uploads - when merging upload chunks, this determines the number of bytes read to copy to the destination file. Defaults to 6 MiB.
* ``SENDFILE_BACKEND``: which backend to use for authorization-secured upload downloads. Defaults to sendfile.backends.nginx. See `django-sendfile2 <https://pypi.org/project/django-sendfile2/>`_ for available backends. Defaults to: ``django_sendfile.backends.nginx``.
* ``LOOSE_FK_LOCAL_BASE_URLS``: explicitly list the allowed prefixes of local urls. Defaults to an empty list. This setting can be used to separate local and external urls, when Open Zaak and other services are deployed within the same domain or API Gateway. If this setting is not defined, all urls with the same host as in the request are considered local. Example: ``LOOSE_FK_LOCAL_BASE_URLS=http://api.example.nl/ozgv-t/zaken/,http://api.example.nl/ozgv-t/catalogi/,http://api.example.nl/ozgv-t/autorisaties/``. Defaults to: ``[]``.
* ``JWT_EXPIRY``: duration a JWT is considered to be valid, in seconds. Defaults to: ``3600``.
* ``JWT_LEEWAY``: JWT validation has a time aspect, usually in the form of the ``iat`` and ``nbf`` claims. Clock drift between server and client can occur. This setting allows specifying the leeway in seconds, and defaults to ``0`` (no leeway). It is advised to not make this larger than a couple of minutes.
* ``CMIS_ENABLED``: whether to enable the CMIS adapter. Defaults to: ``False``.
* ``CMIS_MAPPER_FILE``: name of the file containing the mapping between the Django and Document Management System names for document properties. See the installation section for more details. Defaults to: ``/home/steven/Documents/VNG/open-zaak/config/cmis_mapper.json``.
* ``CMIS_URL_MAPPING_ENABLED``: enable the URL shortener when using the CMIS adapter. Defaults to: ``False``.
* ``ZAAK_EIGENSCHAP_WAARDE_VALIDATION``: if this variable is set to ``true``, ``yes`` or ``1``, ``ZaakEigenschap.waarde`` property would be validated against the related ``Eigenschap.specificatie``. Defaults to: ``False``.
* ``IMPORT_DOCUMENTEN_BASE_DIR``: a string value which specifies the absolute path of a directory used for bulk importing ``EnkelvoudigInformatieObject``'s. This value is used to determine the file path for each row in the import metadata file. By default this is the same directory as the projects directory (``BASE_DIR``).
* ``IMPORT_DOCUMENTEN_BATCH_SIZE``: is the number of rows that will be processed at a time. Used for bulk importing ``EnkelvoudigInformatieObject``'s. Defaults to: ``500``.





Initial superuser creation (Docker only)
----------------------------------------

A clean installation of Objects API comes without pre-installed or pre-configured admin
user by default.

Users of Objects API can opt-in to provision an initial superuser via environment
variables. The user will only be created if it doesn't exist yet.

* ``OBJECTS_SUPERUSER_USERNAME``: specify the username of the superuser to create. Setting
  this to a non-empty value will enable the creation of the superuser. Default empty.
* ``OBJECTS_SUPERUSER_EMAIL``: specify the e-mail address to configure for the superuser.
  Defaults to `admin@admin.org`. Only has an effect if ``OBJECTS_SUPERUSER_USERNAME`` is set.
* ``OBJECTS_SUPERUSER_PASSWORD``: specify the password for the superuser. Default empty,
  which means the superuser will be created _without_ password. Only has an effect
  if ``OBJECTS_SUPERUSER_USERNAME`` is set.

Initial configuration
---------------------

Both Objects API and Objecttypes API support `setup_configuration` management command,
which allows configuration via environment variables.
All these environment variables are described at :ref:`command line <installation_config_cli>`.



Specifying the environment variables
=====================================

There are two strategies to specify the environment variables:

* provide them in a ``.env`` file
* start the component processes (with uwsgi/gunicorn/celery) in a process
  manager that defines the environment variables

Providing a .env file
---------------------

This is the most simple setup and easiest to debug. The ``.env`` file must be
at the root of the project - i.e. on the same level as the ``src`` directory (
NOT *in* the ``src`` directory).

The syntax is key-value:

.. code::

   SOME_VAR=some_value
   OTHER_VAR="quoted_value"


Provide the envvars via the process manager
-------------------------------------------

If you use a process manager (such as supervisor/systemd), use their techniques
to define the envvars. The component will pick them up out of the box.
