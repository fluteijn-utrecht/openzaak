# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import csv
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.db import IntegrityError, OperationalError
from django.conf import settings
from django.test import TestCase, override_settings

import requests_mock
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.documenten.import_utils import DocumentRow
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.documenten.tasks import import_documents
from openzaak.components.documenten.tests.factories import (
    DocumentRowFactory,
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.documenten.tests.utils import (
    get_catalogus_response,
    get_informatieobjecttype_response,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.import_data.models import (
    ImportRowResultChoices,
    ImportStatusChoices,
    ImportTypeChoices,
)
from openzaak.import_data.tests.factories import ImportFactory
from openzaak.import_data.tests.utils import ImportTestMixin, get_temporary_dir
from openzaak.tests.utils.mocks import MockSchemasMixin
from openzaak.utils.fields import get_default_path


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    IMPORT_DOCUMENTEN_BASE_DIR=get_temporary_dir(),
    IMPORT_DOCUMENTEN_BATCH_SIZE=2,
)
class ImportDocumentTestCase(ImportTestMixin, MockSchemasMixin, TestCase):
    mocker_attr = "requests_mock"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        cls.informatieobjecttype = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/"
            "b71f72ef-198d-44d8-af64-ae1932df830a"
        )

        Service.objects.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

    def setUp(self):
        self.requests_mock = requests_mock.Mocker()
        self.requests_mock.start()

        self.requests_mock.get(
            self.informatieobjecttype,
            json=get_informatieobjecttype_response(
                self.catalogus, self.informatieobjecttype
            ),
        )
        self.requests_mock.get(
            self.catalogus,
            json=get_catalogus_response(self.catalogus, self.informatieobjecttype),
        )

        self.addCleanup(self.requests_mock.stop)

        super().setUp()

    def test_simple_import(self):
        zaken = {1: ZaakFactory(), 2: ZaakFactory()}

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid=str(zaken[1].uuid),
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
                uuid=str(uuid4()),
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-3.docx",
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-4.docx",
                zaak_uuid=str(zaken[2].uuid),
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 4)

        self.assertEqual(import_instance.total, 4)
        self.assertEqual(import_instance.processed, 4)
        self.assertEqual(import_instance.processed_invalid, 0)
        self.assertEqual(import_instance.processed_successfully, 4)
        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 5)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        self.assertTrue(
            all((row[-1] == ImportRowResultChoices.imported.label) for row in rows[1:])
        )

        # no comments on all the rows
        self.assertTrue(all((row[-2] == "") for row in rows[1:]))

    def test_total_smaller_than_batch_size(self):
        zaken = {1: ZaakFactory()}

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid=str(zaken[1].uuid),
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)

        self.assertEqual(import_instance.total, 1)
        self.assertEqual(import_instance.processed, 1)
        self.assertEqual(import_instance.processed_invalid, 0)
        self.assertEqual(import_instance.processed_successfully, 1)
        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 2)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        self.assertTrue(
            all((row[-1] == ImportRowResultChoices.imported.label) for row in rows[1:])
        )

        # no comments on all the rows
        self.assertTrue(all((row[-2] == "") for row in rows[1:]))

    def test_last_batch_is_not_full_batch(self):
        zaken = {1: ZaakFactory(), 2: ZaakFactory()}

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid=str(zaken[1].uuid),
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
                uuid=str(uuid4()),
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-3.docx",
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-4.docx",
                zaak_uuid=str(zaken[2].uuid),
            ),
            5: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-5.docx",
                zaak_uuid=str(zaken[1].uuid),
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 5)

        self.assertEqual(import_instance.total, 5)
        self.assertEqual(import_instance.processed, 5)
        self.assertEqual(import_instance.processed_invalid, 0)
        self.assertEqual(import_instance.processed_successfully, 5)
        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 6)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        self.assertTrue(
            all((row[-1] == ImportRowResultChoices.imported.label) for row in rows[1:])
        )

        # no comments on all the rows
        self.assertTrue(all((row[-2] == "") for row in rows[1:]))

    def test_batch_validation_errors(self):
        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                uuid="foobar",  # Note the incorrect uuid
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-3.docx",
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-4.docx",
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 3)

        self.assertEqual(import_instance.total, 4)
        self.assertEqual(import_instance.processed, 4)
        self.assertEqual(import_instance.processed_invalid, 1)
        self.assertEqual(import_instance.processed_successfully, 3)
        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 5)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        success_rows = (3, 4, 5)  # note the header row

        for row_index, row in enumerate(rows, start=1):
            if row_index == 1:
                continue

            with self.subTest(row_index=row_index, row=row):
                if row_index not in success_rows:
                    self.assertEqual(row[-1], ImportRowResultChoices.not_imported.label)

                    self.assertIn("not a valid UUID", row[-2])

                    continue

                self.assertEqual(row[-1], ImportRowResultChoices.imported.label)

                self.assertEqual(row[-2], "")

    @patch("openzaak.components.documenten.tasks.uuid4")
    @patch(
        "openzaak.components.documenten.tasks.EnkelvoudigInformatieObject.objects.bulk_create",
        autospec=True,
    )
    def test_database_connection_loss(self, mocked_bulk_create, mocked_uuid):
        zaken = {1: ZaakFactory(), 2: ZaakFactory()}

        absent_files = ("test-file-3.docx", "test-file-4.docx")

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid=str(zaken[1].uuid),
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad=absent_files[0],
                uuid=str(uuid4()),
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad=absent_files[1],
                zaak_uuid=str(zaken[2].uuid),
                uuid=str(uuid4()),
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        random_eios = EnkelvoudigInformatieObjectFactory.create_batch(
            size=2, informatieobjecttype=self.informatieobjecttype
        )

        mocked_bulk_create.side_effect = (random_eios, OperationalError)

        mocked_uuid.side_effect = [eio.uuid for eio in random_eios]

        import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 2)

        self.assertEqual(import_instance.total, 4)
        self.assertEqual(import_instance.processed, 4)
        self.assertEqual(import_instance.processed_invalid, 2)
        self.assertEqual(import_instance.processed_successfully, 2)
        self.assertEqual(import_instance.status, ImportStatusChoices.error)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 5)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        error_rows = (4, 5)

        for row_index, row in enumerate(rows, start=1):
            if row_index == 1:  # header row
                continue

            with self.subTest(row_index=row_index, row=row):
                if row_index in error_rows:
                    self.assertEqual(row[-1], ImportRowResultChoices.not_imported.label)
                    self.assertIn("Unable to load row due to batch error:", row[-2])

                    continue

                self.assertEqual(row[-1], ImportRowResultChoices.imported.label)
                self.assertEqual(row[-2], "")

        default_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        for filename in absent_files:
            expected_path = Path(default_path / filename)

            with self.subTest(filename=filename):
                self.assertFalse(expected_path.exists())

    @patch("openzaak.components.documenten.tasks.uuid4")
    @patch(
        "openzaak.components.documenten.tasks.EnkelvoudigInformatieObject.objects.bulk_create",
        autospec=True,
    )
    def test_integrity_error(self, mocked_bulk_create, mocked_uuid):
        zaken = {1: ZaakFactory(), 2: ZaakFactory()}

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid=str(zaken[1].uuid),
                uuid=str(uuid4()),
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
                uuid=str(uuid4()),
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-3.docx",
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-4.docx",
                zaak_uuid=str(zaken[2].uuid),
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        random_eios = EnkelvoudigInformatieObjectFactory.create_batch(
            size=2, informatieobjecttype=self.informatieobjecttype
        )

        mocked_bulk_create.side_effect = (IntegrityError, random_eios)

        mocked_uuid.side_effect = [eio.uuid for eio in random_eios]

        import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 2)

        self.assertEqual(import_instance.total, 4)
        self.assertEqual(import_instance.processed, 4)
        self.assertEqual(import_instance.processed_invalid, 2)
        self.assertEqual(import_instance.processed_successfully, 2)
        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 5)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        error_rows = (2, 3)

        for row_index, row in enumerate(rows, start=1):
            if row_index == 1:  # header row
                continue

            with self.subTest(row_index=row_index, row=row):
                if row_index in error_rows:
                    self.assertEqual(row[-1], ImportRowResultChoices.not_imported.label)
                    self.assertIn("Unable to load row due to batch error:", row[-2])

                    continue

                self.assertEqual(row[-1], ImportRowResultChoices.imported.label)
                self.assertEqual(row[-2], "")

        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

    def test_unknown_zaak_uuid(self):
        zaken = {1: ZaakFactory()}

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid="36df518e-7dff-4af3-be96-ccca0c6e6a2e",  # unknown
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
                uuid=str(uuid4()),
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-3.docx",
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-4.docx",
                zaak_uuid=str(zaken[1].uuid),
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 3)

        self.assertEqual(import_instance.total, 4)
        self.assertEqual(import_instance.processed, 4)
        self.assertEqual(import_instance.processed_invalid, 1)
        self.assertEqual(import_instance.processed_successfully, 3)
        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 5)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        error_row = 2

        for row_index, row in enumerate(rows, start=1):
            if row_index == 1:  # header row
                continue

            with self.subTest(row_index=row_index, row=row):
                if row_index == error_row:
                    self.assertEqual(row[-1], ImportRowResultChoices.not_imported.label)
                    self.assertEqual(row[-2], "Zaak ID specified for row 2 is unknown.")

                    continue

                self.assertEqual(row[-1], ImportRowResultChoices.imported.label)
                self.assertEqual(row[-2], "")

    def test_zaak_integrity_error(self):
        zaak = ZaakFactory(uuid="b0f3681d-945a-4b30-afcb-12cad0a3eeaf")

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid=str(zaak.uuid),
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
                uuid=str(uuid4()),
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-3.docx",
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-4.docx",
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        with patch(
            "openzaak.components.documenten.tasks.ZaakInformatieObject.save"
        ) as mocked_save:
            mocked_save.side_effect = IntegrityError

            import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 2)

        self.assertEqual(import_instance.total, 4)
        self.assertEqual(import_instance.processed, 4)
        self.assertEqual(import_instance.processed_invalid, 2)
        self.assertEqual(import_instance.processed_successfully, 2)
        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

        report_path = Path(import_instance.report_file.path)

        with open(report_path, "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 5)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        error_rows = (2, 3)

        for row_index, row in enumerate(rows, start=1):
            if row_index == 1:  # header row
                continue

            with self.subTest(row_index=row_index, row=row):
                if row_index in error_rows:
                    self.assertEqual(row[-1], ImportRowResultChoices.not_imported.label)

                    if row_index == 2:
                        self.assertIn(
                            "Unable to couple row 2 to ZAAK b0f3681d-945a-4b30-afcb-12cad0a3eeaf:",
                            row[-2],
                        )
                    else:
                        self.assertIn(
                            "Unable to load row due to database error", row[-2]
                        )

                    continue

                self.assertEqual(row[-1], ImportRowResultChoices.imported.label)
                self.assertEqual(row[-2], "")

    def test_zaak_database_error(self):
        zaak = ZaakFactory(uuid="b0f3681d-945a-4b30-afcb-12cad0a3eeaf")

        import_data = {
            1: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-1.docx",
                zaak_uuid=str(zaak.uuid),
            ),
            2: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-2.docx",
                uuid=str(uuid4()),
            ),
            3: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-3.docx",
            ),
            4: DocumentRowFactory(
                informatieobjecttype=self.informatieobjecttype,
                bestandspad="test-file-4.docx",
            ),
        }

        import_file = StringIO()

        csv_writer = csv.writer(import_file, delimiter=",", quotechar='"')
        csv_writer.writerow(DocumentRow.export_headers)

        for index, row in import_data.items():
            csv_writer.writerow(row)

        import_file.seek(0)

        self.addCleanup(import_file.close)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_file.read(),
            total=0,
            report_file=None,
        )

        with patch(
            "openzaak.components.documenten.tasks.ZaakInformatieObject.save"
        ) as mocked_save:
            mocked_save.side_effect = OperationalError

            import_documents(import_instance.pk)

        import_instance.refresh_from_db()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 0)

        self.assertEqual(import_instance.total, 4)
        self.assertEqual(import_instance.processed, 2)
        self.assertEqual(import_instance.processed_invalid, 2)
        self.assertEqual(import_instance.processed_successfully, 0)
        self.assertEqual(import_instance.status, ImportStatusChoices.error)

        report_path = Path(import_instance.report_file.path)

        with open(str(report_path), "r") as report_file:
            csv_reader = csv.reader(report_file, delimiter=",", quotechar='"')
            rows = [row for row in csv_reader]

        self.addCleanup(report_path.unlink)

        self.assertEqual(len(rows), 3)
        self.assertEqual(DocumentRow.export_headers, rows[0])

        for row_index, row in enumerate(rows, start=1):
            if row_index == 1:  # header row
                continue

            with self.subTest(row_index=row_index, row=row):
                self.assertEqual(row[-1], ImportRowResultChoices.not_imported.label)

                if row_index == 2:
                    self.assertIn(
                        "Unable to couple row 2 to ZAAK b0f3681d-945a-4b30-afcb-12cad0a3eeaf:",
                        row[-2],
                    )
                else:
                    self.assertIn("Unable to load row due to database error", row[-2])
