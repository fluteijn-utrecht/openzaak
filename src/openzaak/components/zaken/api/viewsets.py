import logging

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from vng_api_common.audittrails.viewsets import (
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    AuditTrailViewSet,
    AuditTrailViewsetMixin,
)
from vng_api_common.filters import Backend
from vng_api_common.geo import GeoMixin
from vng_api_common.notifications.viewsets import (
    NotificationCreateMixin,
    NotificationDestroyMixin,
    NotificationViewSetMixin,
)
from vng_api_common.search import SearchMixin
from vng_api_common.utils import lookup_kwargs_to_filters
from vng_api_common.viewsets import CheckQueryParamsMixin, NestedViewSetMixin

from openzaak.components.besluiten.models import Besluit
from openzaak.notificaties.mixins import FailedNotificationMixin
from openzaak.utils.data_filtering import ListFilterByAuthorizationsMixin

from ..models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakBesluit,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)
from .audits import AUDIT_ZRC
from .filters import (
    KlantContactFilter,
    ResultaatFilter,
    RolFilter,
    StatusFilter,
    ZaakFilter,
    ZaakInformatieObjectFilter,
    ZaakObjectFilter,
)
from .kanalen import KANAAL_ZAKEN
from .permissions import ZaakAuthRequired, ZaakNestedAuthRequired
from .scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    SCOPEN_ZAKEN_HEROPENEN,
)
from .serializers import (
    KlantContactSerializer,
    ResultaatSerializer,
    RolSerializer,
    StatusSerializer,
    ZaakBesluitSerializer,
    ZaakEigenschapSerializer,
    ZaakInformatieObjectSerializer,
    ZaakObjectSerializer,
    ZaakSerializer,
    ZaakZoekSerializer,
)

logger = logging.getLogger(__name__)


class ZaakViewSet(
    FailedNotificationMixin,
    NotificationViewSetMixin,
    AuditTrailViewsetMixin,
    GeoMixin,
    SearchMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKen.

    Een zaak mag (in principe) niet meer gewijzigd worden als de
    `archiefstatus` een andere status heeft dan "nog_te_archiveren". Voor
    praktische redenen is er geen harde validatie regel aan de provider kant.

    create:
    Maak een ZAAK aan.

    Indien geen identificatie gegeven is, dan wordt deze automatisch
    gegenereerd. De identificatie moet uniek zijn binnen de bronorganisatie.

    **Er wordt gevalideerd op**:
    - `zaaktype` moet een geldige URL zijn.
    - `zaaktype` is geen concept (`zaaktype.concept` = False)
    - `laatsteBetaaldatum` mag niet in de toekomst liggen.
    - `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie
      "nvt" is.
    - `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren"
      hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut
      `status` de waarde "gearchiveerd" heeft.

    list:
    Alle ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    **Opmerking**
    - er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd
      bent.

    retrieve:
    Een specifieke ZAAK opvragen.

    Een specifieke ZAAK opvragen.

    update:
    Werk een ZAAK in zijn geheel bij.

    **Er wordt gevalideerd op**
    - `zaaktype` mag niet gewijzigd worden.
    - `zaaktype` is geen concept (`zaaktype.concept` = False)
    - `identificatie` mag niet gewijzigd worden.
    - `laatsteBetaaldatum` mag niet in de toekomst liggen.
    - `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie
      "nvt" is.
    - `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren"
      hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut
      `status` de waarde "gearchiveerd" heeft.

    **Opmerkingen**
    - er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd
      bent.
    - zaaktype zal in de toekomst niet-wijzigbaar gemaakt worden.
    - indien een zaak heropend moet worden, doe dit dan door een nieuwe status
      toe te voegen die NIET de eindstatus is.
      Zie de `Status` resource.

    partial_update:
    Werk een ZAAK deels bij.

    **Er wordt gevalideerd op**
    - `zaaktype` mag niet gewijzigd worden.
    - `zaaktype` is geen concept (`zaaktype.concept` = False)
    - `identificatie` mag niet gewijzigd worden.
    - `laatsteBetaaldatum` mag niet in de toekomst liggen.
    - `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie
      "nvt" is.
    - `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren"
      hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut
      `status` de waarde "gearchiveerd" heeft.

    **Opmerkingen**
    - er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd
      bent.
    - zaaktype zal in de toekomst niet-wijzigbaar gemaakt worden.
    - indien een zaak heropend moet worden, doe dit dan door een nieuwe status
      toe te voegen die NIET de eindstatus is. Zie de `Status` resource.

    destroy:
    Verwijder een ZAAK.

    **De gerelateerde resources zijn hierbij**
    - `zaak` - de deelzaken van de verwijderde hoofzaak
    - `status` - alle statussen van de verwijderde zaak
    - `resultaat` - het resultaat van de verwijderde zaak
    - `rol` - alle rollen bij de zaak
    - `zaakobject` - alle zaakobjecten bij de zaak
    - `zaakeigenschap` - alle eigenschappen van de zaak
    - `zaakkenmerk` - alle kenmerken van de zaak
    - `zaakinformatieobject` - dit moet door-cascaden naar de Documenten API,
      zie ook: https://github.com/VNG-Realisatie/gemma-zaken/issues/791 (TODO)
    - `klantcontact` - alle klantcontacten bij een zaak
    """

    queryset = (
        Zaak.objects.select_related("_zaaktype")
        .prefetch_related(
            "deelzaken",
            "relevante_andere_zaken",
            "zaakkenmerk_set",
            "resultaat",
            models.Prefetch(
                "status_set", Status.objects.order_by("-datum_status_gezet")
            ),
        )
        .order_by("-pk")
    )
    serializer_class = ZaakSerializer
    search_input_serializer_class = ZaakZoekSerializer
    filter_backends = (Backend, OrderingFilter)
    filterset_class = ZaakFilter
    ordering_fields = ("startdatum",)
    lookup_field = "uuid"
    pagination_class = PageNumberPagination

    permission_classes = (ZaakAuthRequired,)
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "_zoek": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    @action(methods=("post",), detail=False)
    def _zoek(self, request, *args, **kwargs):
        """
        Voer een (geo)-zoekopdracht uit op ZAAKen.

        Zoeken/filteren gaat normaal via de `list` operatie, deze is echter
        niet geschikt voor geo-zoekopdrachten.
        """
        search_input = self.get_search_input()

        within = search_input["zaakgeometrie"]["within"]
        queryset = self.filter_queryset(self.get_queryset()).filter(
            zaakgeometrie__within=within
        )

        return self.get_search_output(queryset)

    _zoek.is_search_action = True

    def perform_update(self, serializer):
        """
        Perform the update of the Case.

        After input validation and before DB persistance we need to check
        scope-related permissions. Only SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN scope
        allows to alter closed cases

        :raises: PermissionDenied if attempting to alter a closed case with
        insufficient permissions

        """
        zaak = self.get_object()
        zaak_data = self.get_serializer(zaak).data

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
            zaaktype=zaak_data["zaaktype"],
            vertrouwelijkheidaanduiding=zaak_data["vertrouwelijkheidaanduiding"],
            init_component=self.queryset.model._meta.app_label,
        ):
            if zaak.einddatum:
                msg = "Modifying a closed case with current scope is forbidden"
                raise PermissionDenied(detail=msg)
        super().perform_update(serializer)

    def perform_destroy(self, instance: Zaak):
        if instance.besluit_set.exists():
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "All related Besluit objects should be destroyed before destroying the zaak"
                    )
                },
                code="pending-besluit-relation",
            )

        super().perform_destroy(instance)


class StatusViewSet(
    FailedNotificationMixin,
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en beheren van zaakstatussen.

    list:
    Alle STATUSsen van ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke STATUS van een ZAAK opvragen.

    Een specifieke STATUS van een ZAAK opvragen.

    create:
    Maak een STATUS aan voor een ZAAK.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - geldigheid URL naar het STATUSTYPE
    - indien het de eindstatus betreft, dan moet het attribuut
      `indicatieGebruiksrecht` gezet zijn op alle informatieobjecten die aan
      de zaak gerelateerd zijn

    **Opmerkingen**
    - Indien het statustype de eindstatus is (volgens het ZTC), dan wordt de
      zaak afgesloten door de einddatum te zetten.

    """

    queryset = Status.objects.select_related("statustype", "zaak").all()
    serializer_class = StatusSerializer
    filterset_class = StatusFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE
        | SCOPE_STATUSSEN_TOEVOEGEN
        | SCOPEN_ZAKEN_HEROPENEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def perform_create(self, serializer):
        """
        Perform the create of the Status.

        After input validation and before DB persistance we need to check
        scope-related permissions. Three scopes are allowed to create new
        Status objects:
        - create initial status
        - create initial status and subsequent statuses until the case is closed
        - create any status before or after the case is closed

        :raises: PermissionDenied if attempting to create another Status with
          insufficient permissions
        """
        zaak = serializer.validated_data["zaak"]
        zaak_data = ZaakSerializer(zaak, context={"request": self.request}).data
        component = self.queryset.model._meta.app_label

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPE_STATUSSEN_TOEVOEGEN | SCOPEN_ZAKEN_HEROPENEN,
            zaaktype=zaak_data["zaaktype"],
            vertrouwelijkheidaanduiding=zaak_data["vertrouwelijkheidaanduiding"],
            init_component=component,
        ):
            if zaak.status_set.exists():
                msg = f"Met de '{SCOPE_ZAKEN_CREATE}' scope mag je slechts 1 status zetten"
                raise PermissionDenied(detail=msg)

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPEN_ZAKEN_HEROPENEN,
            zaaktype=zaak_data["zaaktype"],
            vertrouwelijkheidaanduiding=zaak_data["vertrouwelijkheidaanduiding"],
            init_component=component,
        ):
            if zaak.einddatum:
                msg = "Reopening a closed case with current scope is forbidden"
                raise PermissionDenied(detail=msg)

        super().perform_create(serializer)


class ZaakObjectViewSet(
    FailedNotificationMixin,
    CheckQueryParamsMixin,
    NotificationCreateMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailCreateMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKOBJECTen.

    create:
    Maak een ZAAKOBJECT aan.

    Maak een ZAAKOBJECT aan.

    list:
    Alle ZAAKOBJECTen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifiek ZAAKOBJECT opvragen.

    Een specifiek ZAAKOBJECT opvragen.
    """

    queryset = ZaakObject.objects.select_related("zaak").all()
    serializer_class = ZaakObjectSerializer
    filterset_class = ZaakObjectFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE | SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class ZaakInformatieObjectViewSet(
    FailedNotificationMixin,
    NotificationCreateMixin,
    NotificationDestroyMixin,
    AuditTrailViewsetMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    viewsets.ModelViewSet,
):

    """
    Opvragen en bewerken van ZAAK-INFORMATIEOBJECT relaties.

    create:
    Maak een ZAAK-INFORMATIEOBJECT relatie aan.

    Er worden twee types van
    relaties met andere objecten gerealiseerd:

    **Er wordt gevalideerd op**
    - geldigheid zaak URL
    - geldigheid informatieobject URL
    - de combinatie informatieobject en zaak moet uniek zijn

    **Opmerkingen**
    - De registratiedatum wordt door het systeem op 'NU' gezet. De `aardRelatie`
      wordt ook door het systeem gezet.
    - Bij het aanmaken wordt ook in de Documenten API de gespiegelde relatie aangemaakt,
      echter zonder de relatie-informatie.

    Registreer welk(e) INFORMATIEOBJECT(en) een ZAAK kent.

    **Er wordt gevalideerd op**
    - geldigheid informatieobject URL
    - uniek zijn van relatie ZAAK-INFORMATIEOBJECT

    list:
    Alle ZAAK-INFORMATIEOBJECT relaties opvragen.

    Deze lijst kan gefilterd wordt met querystringparameters.

    retrieve:
    Een specifieke ZAAK-INFORMATIEOBJECT relatie opvragen.

    Een specifieke ZAAK-INFORMATIEOBJECT relatie opvragen.

    update:
    Werk een ZAAK-INFORMATIEOBJECT relatie in zijn geheel bij.

    Je mag enkel de gegevens
    van de relatie bewerken, en niet de relatie zelf aanpassen.

    **Er wordt gevalideerd op**
    - informatieobject URL en zaak URL mogen niet veranderen

    partial_update:
    Werk een ZAAK-INFORMATIEOBJECT relatie in deels bij.

    Je mag enkel de gegevens
    van de relatie bewerken, en niet de relatie zelf aanpassen.

    **Er wordt gevalideerd op**
    - informatieobject URL en zaak URL mogen niet veranderen

    destroy:
    Verwijder een ZAAK-INFORMATIEOBJECT relatie.

    De gespiegelde relatie in de Documenten API wordt door de Zaken API
    verwijderd. Consumers kunnen dit niet handmatig doen.
    """

    queryset = (
        ZaakInformatieObject.objects.select_related("zaak", "_informatieobject")
        .prefetch_related("_informatieobject__enkelvoudiginformatieobject_set")
        .all()
    )
    filterset_class = ZaakInformatieObjectFilter
    serializer_class = ZaakInformatieObjectSerializer
    lookup_field = "uuid"
    notifications_kanaal = KANAAL_ZAKEN
    notifications_main_resource_key = "zaak"
    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE | SCOPE_ZAKEN_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN
        | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
        | SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    }
    audit = AUDIT_ZRC


class ZaakEigenschapViewSet(
    FailedNotificationMixin,
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    NestedViewSetMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKEIGENSCHAPpen

    create:
    Maak een ZAAKEIGENSCHAP aan.

    Maak een ZAAKEIGENSCHAP aan.

    list:
    Alle ZAAKEIGENSCHAPpen opvragen.

    Alle ZAAKEIGENSCHAPpen opvragen.

    retrieve:
    Een specifieke ZAAKEIGENSCHAP opvragen.

    Een specifieke ZAAKEIGENSCHAP opvragen.
    """

    queryset = ZaakEigenschap.objects.select_related("zaak", "eigenschap").all()
    serializer_class = ZaakEigenschapSerializer
    permission_classes = (ZaakNestedAuthRequired,)
    lookup_field = "uuid"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
    }
    parent_retrieve_kwargs = {"zaak_uuid": "uuid"}
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def _get_zaak(self):
        if not hasattr(self, "_zaak"):
            filters = lookup_kwargs_to_filters(self.parent_retrieve_kwargs, self.kwargs)
            self._zaak = get_object_or_404(Zaak, **filters)
        return self._zaak


class KlantContactViewSet(
    CheckQueryParamsMixin,
    FailedNotificationMixin,
    NotificationCreateMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailCreateMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van KLANTCONTACTen.

    create:
    Maak een KLANTCONTACT bij een ZAAK aan.

    Indien geen identificatie gegeven is, dan wordt deze automatisch
    gegenereerd.

    list:
    Alle KLANTCONTACTen opvragen.

    Alle KLANTCONTACTen opvragen.

    retrieve:
    Een specifiek KLANTCONTACT bij een ZAAK opvragen.

    Een specifiek KLANTCONTACT bij een ZAAK opvragen.
    """

    queryset = KlantContact.objects.select_related("zaak").all()
    serializer_class = KlantContactSerializer
    filterset_class = KlantContactFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class RolViewSet(
    FailedNotificationMixin,
    NotificationCreateMixin,
    NotificationDestroyMixin,
    AuditTrailCreateMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van ROL relatie tussen een ZAAK en een BETROKKENE.

    list:
    Alle ROLlen bij ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke ROL bij een ZAAK opvragen.

    Een specifieke ROL bij een ZAAK opvragen.

    destroy:
    Verwijder een ROL van een ZAAK.

    Verwijder een ROL van een ZAAK.

    create:
    Maak een ROL aan bij een ZAAK.

    Maak een ROL aan bij een ZAAK.

    """

    queryset = (
        Rol.objects.select_related("roltype", "zaak")
        .prefetch_related(
            "natuurlijkpersoon",
            "nietnatuurlijkpersoon",
            "vestiging",
            "organisatorischeeenheid",
            "medewerker",
        )
        .all()
    )
    serializer_class = RolSerializer
    filterset_class = RolFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class ResultaatViewSet(
    FailedNotificationMixin,
    NotificationViewSetMixin,
    AuditTrailViewsetMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en beheren van resultaten.

    list:
    Alle RESULTAATen van ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifiek RESULTAAT opvragen.

    Een specifiek RESULTAAT opvragen.

    create:
    Maak een RESULTAAT bij een ZAAK aan.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - geldigheid URL naar het RESULTAATTYPE

    update:
    Werk een RESULTAAT in zijn geheel bij.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - het RESULTAATTYPE mag niet gewijzigd worden

    partial_update:
    Werk een RESULTAAT deels bij.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - het RESULTAATTYPE mag niet gewijzigd worden

    destroy:
    Verwijder een RESULTAAT van een ZAAK.

    Verwijder een RESULTAAT van een ZAAK.

    """

    queryset = Resultaat.objects.select_related("resultaattype", "zaak").all()
    serializer_class = ResultaatSerializer
    filterset_class = ResultaatFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class ZaakAuditTrailViewSet(AuditTrailViewSet):
    """
    Opvragen van Audit trails horend bij een ZAAK.

    list:
    Alle audit trail regels behorend bij de ZAAK.

    Alle audit trail regels behorend bij de ZAAK.

    retrieve:
    Een specifieke audit trail regel opvragen.

    Een specifieke audit trail regel opvragen.
    """

    main_resource_lookup_field = "zaak_uuid"


class ZaakBesluitViewSet(
    FailedNotificationMixin,
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    NestedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    # Because of the database-FK nature, ZaakBesluit is pretty much an alias
    # for Besluit. We are handling Besluit-objects here and filtering them on
    # the relevant Zaak.
    """
    Opvragen en beheren van zaak-besluiten.

    list:
    Alle ZAAKBESLUITen opvragen.

    Alle ZAAKBESLUITen opvragen.

    retrieve:
    Een specifiek ZAAKBESLUIT opvragen.

    Een specifiek ZAAKBESLUIT opvragen.

    create:
    Maak een ZAAKBESLUIT aan.

    **LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**

    De Besluiten API gebruikt dit endpoint om relaties te synchroniseren,
    daarom is dit endpoint in de Zaken API geimplementeerd.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK

    destroy:
    Verwijder een ZAAKBESLUIT.

    **LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**

    De Besluiten API gebruikt dit endpoint om relaties te synchroniseren,
    daarom is dit endpoint in de Zaken API geimplementeerd.
    """

    queryset = ZaakBesluit.objects.none()  # required for vng-api-common
    serializer_class = ZaakBesluitSerializer
    lookup_field = "uuid"
    parent_retrieve_kwargs = {"zaak_uuid": "uuid"}
    permission_classes = (ZaakNestedAuthRequired,)
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def _get_zaak(self):
        if not hasattr(self, "_zaak"):
            self._zaak = get_object_or_404(Zaak, uuid=self.kwargs["zaak_uuid"])
        return self._zaak

    def get_queryset(self) -> models.QuerySet:
        zaak_uuid = self.kwargs.get("zaak_uuid")  # empty on drf-yasg introspection
        # filter directly on the FK - since `ZaakBesluit` is only relevant
        # for local fk zaken
        return ZaakBesluit.objects.filter(_zaak__uuid=zaak_uuid)

    def perform_create(self, serializer):
        """
        Handle the creation logic.

        Nothing extra happens here, since the creation is entirely managed via
        the Besluit resource. We just perform some extra sanity checks in the
        serializer.
        """
        besluit = serializer.validated_data["besluit"]
        self._instance = ZaakBesluit.objects.get(pk=besluit.pk)
        serializer.instance = self._instance

    def get_audittrail_instance(self, response):
        return self._instance

    def get_audittrail_main_object_url(self, data, main_resource) -> str:
        return reverse(
            "zaak-detail",
            request=self.request,
            kwargs={"uuid": self.kwargs["zaak_uuid"]},
        )

    def get_notification_main_object_url(self, data, main_resource) -> str:
        return reverse(
            "zaak-detail",
            request=self.request,
            kwargs={"uuid": self.kwargs["zaak_uuid"]},
        )

    def perform_destroy(self, instance: Besluit):
        """
        'Delete' the relation between zaak & besluit.

        The actual relation information must be updated in the Besluiten API,
        so this is just a check.
        """
        if instance.zaak:
            raise ValidationError(
                {
                    "zaak": _(
                        "Het Besluit verwijst nog naar deze zaak. "
                        "Deze relatie moet eerst verbroken worden."
                    )
                },
                code="inconsistent-relation",
            )

        # nothing to do, the 'relation' info is dealt with through besluit.Besluit
        pass
