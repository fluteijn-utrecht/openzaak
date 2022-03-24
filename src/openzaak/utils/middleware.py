# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from typing import Dict, Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponseNotFound

from rest_framework.response import Response
from rest_framework.reverse import reverse
from vng_api_common.middleware import (
    VERSION_HEADER,
    APIVersionHeaderMiddleware as _APIVersionHeaderMiddleware,
)

from openzaak.config.models import InternalService

from .constants import COMPONENT_MAPPING

logger = logging.getLogger(__name__)

WARNING_HEADER = "Warning"
DEPRECATION_WARNING_CODE = 299


class LogHeadersMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        self.log(request)
        return self.get_response(request) if self.get_response else None

    def log(self, request: HttpRequest):
        logger.debug("Request headers for %s: %r", request.path, request.headers)


def get_version_mapping() -> Dict[str, str]:
    apis = ("autorisaties", "besluiten", "catalogi", "documenten", "zaken")
    version = settings.REST_FRAMEWORK["DEFAULT_VERSION"]

    return {
        reverse(f"api-root-{api}", kwargs={"version": version}): getattr(
            settings, f"{api.upper()}_API_VERSION"
        )
        for api in apis
    }


class APIVersionHeaderMiddleware(_APIVersionHeaderMiddleware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.version_mapping = get_version_mapping()

    def __call__(self, request):
        if self.get_response is None:
            return None

        response = self.get_response(request)

        # not an API response, exit early
        if not isinstance(response, Response):
            return response

        # set the header
        version = self._get_version(request.path)
        if version is not None:
            response[VERSION_HEADER] = version

        return response

    def _get_version(self, path: str) -> Optional[str]:
        for prefix, version in self.version_mapping.items():
            if path.startswith(prefix):
                return version
        return None


class EnabledMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    @staticmethod
    def get_component_type(request):
        url = request.path
        if settings.FORCE_SCRIPT_NAME and url.startswith(settings.FORCE_SCRIPT_NAME):
            url = url.replace(settings.FORCE_SCRIPT_NAME, "", 1)
        # All component names match the first parts of urls
        component = url.strip("/").split("/")[0]
        return COMPONENT_MAPPING.get(component)

    def process_view(self, request, view_func, view_args, view_kwargs):
        component_type = self.get_component_type(request)
        disabled = InternalService.objects.filter(
            api_type=component_type, enabled=False
        ).exists()
        if not disabled:
            return None
        return HttpResponseNotFound()


# See https://github.com/Geonovum/KP-APIs/blob/master/Werkgroep%20API%20strategie/extensies/ext-versionering.md
class Warning:
    def __init__(self, code: int, agent: str, text: str):
        self.code = code
        self.agent = agent
        self.text = text

    def __str__(self):
        return f'{self.code} "{self.agent}" "{self.text}"'


class DeprecationMiddleware:
    """
    Include a header outputting a deprecation warning.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        if self.get_response is None:
            return None

        response = self.get_response(request)

        warning = getattr(request, "_warning", None)
        if warning:
            response[WARNING_HEADER] = str(warning)

        return response

    def process_view(self, request, callback, callback_args, callback_kwargs):
        # not a viewset
        if not hasattr(callback, "cls"):
            return None

        deprecation_msg = getattr(callback.cls, "deprecation_message", None)
        # no deprecation happening
        if not deprecation_msg:
            return None

        request._warning = Warning(
            DEPRECATION_WARNING_CODE,
            request.build_absolute_uri(request.path),
            deprecation_msg,
        )

        return None
