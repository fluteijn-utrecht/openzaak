# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings

from rest_framework import status

from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, serialise_eio

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@override_settings(CMIS_ENABLED=True)
class BesluitDeleteCMISTestCase(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_delete_besluit_cascades_properly(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        BesluitInformatieObjectFactory.create(besluit=besluit, informatieobject=eio_url)
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
