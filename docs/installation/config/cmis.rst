.. _installation_cmis:

CMIS adapter
============

In a default installation of Open Zaak, any document created through the
`Documenten API`_ are stored on disk and their metadata is stored in the 
database. However, it is also possible to store these documents in a Document 
Management System (DMS) using the CMIS standard.

.. _`Documenten API`: https://documenten-api.vng.cloud/api/v1/schema/

The CMIS adapter converts API calls to the Documenten API in Open Zaak, to CMIS 
calls which are sent to the DMS to retrieve, create, update and delete 
documents. This way, the documents are stored in, or retrieved from, the DMS 
and not in or from Open Zaak.

CMIS support
------------

`CMIS 1.0`_ and `CMIS 1.1`_ have various CMIS protocol bindings that can be 
used. Although according to the CMIS specification repositories must implement 
Web Services and AtomPub bindings, some DMS implementation only support one 
and/or recommend the newer Browser bindings.

.. _`CMIS 1.0`: https://docs.oasis-open.org/cmis/CMIS/v1.0/cmis-spec-v1.0.html
.. _`CMIS 1.1`: https://docs.oasis-open.org/cmis/CMIS/v1.1/CMIS-v1.1.html

+----------------------+-----------+-----------+
|                      |  CMIS 1.0 |  CMIS 1.1 |
+======================+===========+===========+
| Web Services binding | Supported |  Untested |
+----------------------+-----------+-----------+
| AtomPub binding      |  Untested |  Untested |
+----------------------+-----------+-----------+
| Browser binding      |    N/A    | Supported |
+----------------------+-----------+-----------+

CMIS support is built in Open Zaak using the `CMIS adapter library`_. For an 
up-to-date list of supported CMIS versions and libraries, please see this 
project's documentation.

.. warning::
   The CMIS adapter is currently an experimental feature. While we have 
   extensive unit test coverage with `Alfresco`_ , we require more "real world" 
   testing before we can label the feature as stable.

.. _`Alfresco`: https://www.alfresco.com/ecm-software/alfresco-community-editions

Using the CMIS adapter
----------------------

1. Create a mapping file to match Documenten API attributes to custom 
   properties in your DMS model. The format is explained in the 
   `CMIS adapter library`_ *Mapping configuration* documentation.

   You can use our `default CMIS mapping`_  for inspiration or just use these 
   as defaults.

   .. _`default CMIS mapping`: https://github.com/open-zaak/open-zaak/blob/master/config/cmis_mapper.json
   .. _`Alfresco model`: https://github.com/open-zaak/open-zaak/blob/master/extension/alfresco-zsdms-model.xml

2. Make sure the content model is loaded in your DMS and matches the CMIS 
   mapping described in step 1. It's important that all attributes are present.
   Some need to be indexed to allow the proper CMIS queries to be executed.

   You can use our `Alfresco model`_ that matches the default mapping. The 
   detailed explanation is described in the `CMIS adapter library`_ 
   *DMS Content model configuration* documentation.

3. Enable the CMIS adapter. In the environment (or ``.env`` file), add or 
   update the variable ``CMIS_ENABLED`` and ``CMIS_MAPPER_FILE``:

    .. code-block:: bash

        # Enables the CMIS-backend and the Open Zaak admin interface for configuring 
        # the DMS settings.
        CMIS_ENABLED = True

        # Absolute path to the mapping of Documenten API attributes to (custom) 
        # properties in your DMS model.
        CMIS_MAPPER_FILE = /path/to/cmis_mapper.json

4. You will need to restart Open Zaak for these changes to take effect.

5. Login to the Open Zaak admin interface (``/admin/``) as superuser.

6. Navigate to **Configuratie > CMIS configuration** and fill in all relevant
   fields.

   The folder structure that is used by Open Zaak is as follows:

7. Save the configuration.

Test the CMIS-configuration
---------------------------

.. todo:: There should be an easy way to test the CMIS configuration.

.. _`CMIS adapter library`: https://github.com/open-zaak/cmis-adapter
