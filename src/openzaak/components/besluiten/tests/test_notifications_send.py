from unittest.mock import patch

from django.test import override_settings
from django.utils.timezone import datetime, make_aware

from djangorestframework_camel_case.util import camelize
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notificaties.models import FailedNotification
from openzaak.utils.tests import JWTAuthMixin

from ..api.serializers import BesluitSerializer
from ..constants import VervalRedenen
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@freeze_time("2018-09-07T00:00:00Z")
@override_settings(NOTIFICATIONS_DISABLED=False)
class SendNotifTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @patch("zds_client.Client.from_url")
    def test_send_notif_create_besluit(self, mock_client, *mocks):
        """
        Check if notifications will be send when Besluit is created
        """
        client = mock_client.return_value
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        url = get_operation_url("besluit_create")
        data = {
            "verantwoordelijkeOrganisatie": "517439943",  # RSIN
            "besluittype": f"http://testserver{besluittype_url}",
            "identificatie": "123123",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        client.create.assert_called_once_with(
            "notificaties",
            {
                "kanaal": "besluiten",
                "hoofdObject": data["url"],
                "resource": "besluit",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2018-09-07T00:00:00Z",
                "kenmerken": {
                    "verantwoordelijkeOrganisatie": "517439943",
                    "besluittype": f"http://testserver{besluittype_url}",
                },
            },
        )

    @patch("zds_client.Client.from_url")
    def test_send_notif_delete_resultaat(self, mock_client):
        """
        Check if notifications will be send when resultaat is deleted
        """
        client = mock_client.return_value
        besluit = BesluitFactory.create()
        besluit_url = get_operation_url("besluit_read", uuid=besluit.uuid)
        besluittype_url = reverse(besluit.besluittype)
        bio = BesluitInformatieObjectFactory.create(besluit=besluit)
        bio_url = get_operation_url("besluitinformatieobject_delete", uuid=bio.uuid)

        response = self.client.delete(bio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        client.create.assert_called_once_with(
            "notificaties",
            {
                "kanaal": "besluiten",
                "hoofdObject": f"http://testserver{besluit_url}",
                "resource": "besluitinformatieobject",
                "resourceUrl": f"http://testserver{bio_url}",
                "actie": "destroy",
                "aanmaakdatum": "2018-09-07T00:00:00Z",
                "kenmerken": {
                    "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                    "besluittype": f"http://testserver{besluittype_url}",
                },
            },
        )


@override_settings(NOTIFICATIONS_DISABLED=False)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluit_create_fail_send_notification_create_db_entry(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        url = get_operation_url("besluit_create")
        data = {
            "verantwoordelijkeOrganisatie": "517439943",  # RSIN
            "besluittype": f"http://testserver{besluittype_url}",
            "identificatie": "123123",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "besluiten")
        self.assertEqual(failed.model, "Besluit")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_besluit_delete_fail_send_notification_create_db_entry(self):
        besluit = BesluitFactory.create()
        url = reverse(besluit)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "besluiten")
        self.assertEqual(failed.model, "Besluit")
        self.assertEqual(failed.instance, failed.data)

    def test_besluitinformatieobject_create_fail_send_notification_create_db_entry(
        self,
    ):
        url = get_operation_url("besluitinformatieobject_create")

        besluit = BesluitFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        besluit_url = reverse(besluit)
        io_url = reverse(io)
        data = {
            "informatieobject": f"http://testserver{io_url}",
            "besluit": f"http://testserver{besluit_url}",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "besluiten")
        self.assertEqual(failed.model, "BesluitInformatieObject")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_besluitinformatieobject_delete_fail_send_notification_create_db_entry(
        self,
    ):
        bio = BesluitInformatieObjectFactory.create()
        url = reverse(bio)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "besluiten")
        self.assertEqual(failed.model, "BesluitInformatieObject")
        self.assertEqual(failed.instance, failed.data)
