# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

from django import forms
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from django_loose_fk.loaders import BaseLoader
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes

from openzaak.components.catalogi.models import (
    BesluitType,
    Catalogus,
    InformatieObjectType,
    ZaakType,
)
from openzaak.utils.admin import AdminContextMixin

from .admin_serializers import CatalogusSerializer
from .constants import RelatedTypeSelectionMethods
from .forms import (
    COMPONENT_TO_FIELDS_MAP,
    COMPONENT_TO_PREFIXES_MAP,
    AutorisatieFormSet,
    VertrouwelijkheidsAanduiding,
    get_scope_choices,
)
from .models import AutorisatieSpec, CatalogusAutorisatie
from .utils import get_related_object


def get_form_data(form: forms.Form) -> Dict[str, Dict]:
    """
    Serialize the form data and errors for the frontend.
    """
    errors = (
        {
            field: [{"msg": next(iter(error)), "code": error.code} for error in _errors]
            for field, _errors in form.errors.as_data().items()
        }
        if form.is_bound
        else {}
    )

    values = {field.name: field.value() for field in form}
    return {
        "errors": errors,
        "values": values,
    }


def is_local_url(autorisatie):
    loader = BaseLoader()
    if autorisatie.component == ComponentTypes.zrc:
        return loader.is_local_url(autorisatie.zaaktype)
    elif autorisatie.component == ComponentTypes.drc:
        return loader.is_local_url(autorisatie.informatieobjecttype)
    elif autorisatie.component == ComponentTypes.brc:
        return loader.is_local_url(autorisatie.besluittype)
    return True


def get_initial_for_component(
    component: str,
    autorisaties: List[Autorisatie],
    spec: Optional[AutorisatieSpec] = None,
    catalogus_autorisaties: Optional[List[CatalogusAutorisatie]] = None,
) -> List[Dict[str, Any]]:
    _related_objs = {}
    _related_objs_external = {}

    internal_autorisaties = []
    external_autorisaties = []

    for autorisatie in autorisaties:
        if is_local_url(autorisatie):
            obj = get_related_object(autorisatie)
            _related_objs[autorisatie.pk] = obj
            internal_autorisaties.append(autorisatie)
        else:
            type_field = COMPONENT_TO_FIELDS_MAP[component]["_autorisatie_type_field"]
            _related_objs_external[autorisatie.pk] = getattr(autorisatie, type_field)
            external_autorisaties.append(autorisatie)

    related_objs = {pk: obj.id for pk, obj in _related_objs.items() if obj is not None}

    initial = []

    if component == ComponentTypes.zrc:
        zaaktype_ids = set(ZaakType.objects.values_list("id", flat=True))

        grouped_by_va = defaultdict(list)
        for autorisatie in internal_autorisaties + external_autorisaties:
            grouped_by_va[autorisatie.max_vertrouwelijkheidaanduiding].append(
                autorisatie
            )

        # if spec is created but no records exist
        # we need to add the spec here
        if spec and spec.max_vertrouwelijkheidaanduiding not in grouped_by_va:
            grouped_by_va[spec.max_vertrouwelijkheidaanduiding] = []

        if (
            catalogus_autorisaties
            and catalogus_autorisaties[0].max_vertrouwelijkheidaanduiding
            not in grouped_by_va
        ):
            grouped_by_va[catalogus_autorisaties[0].max_vertrouwelijkheidaanduiding] = (
                []
            )

        for va, _autorisaties in grouped_by_va.items():
            _initial = {"vertrouwelijkheidaanduiding": va}
            relevant_ids = {
                related_objs[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in related_objs
            }
            relevant_external = [
                _related_objs_external[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in _related_objs_external
            ]

            if spec:
                _initial["related_type_selection"] = (
                    RelatedTypeSelectionMethods.all_current_and_future
                )
            elif zaaktype_ids == relevant_ids:
                _initial["related_type_selection"] = (
                    RelatedTypeSelectionMethods.all_current
                )
            elif catalogus_autorisaties:
                _initial.update(
                    {
                        "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                        "catalogi": [
                            catalogus_autorisatie.catalogus.pk
                            for catalogus_autorisatie in catalogus_autorisaties
                        ],
                    }
                )
            else:
                _initial.update(
                    {
                        "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                        "zaaktypen": relevant_ids,
                        "externe_typen": relevant_external,
                    }
                )
            initial.append(_initial)

    elif component == ComponentTypes.drc:
        informatieobjecttype_ids = set(
            InformatieObjectType.objects.values_list("id", flat=True)
        )

        grouped_by_va = defaultdict(list)
        for autorisatie in internal_autorisaties + external_autorisaties:
            grouped_by_va[autorisatie.max_vertrouwelijkheidaanduiding].append(
                autorisatie
            )

        # if spec is created but no records exist
        # we need to add the spec here
        if spec and spec.max_vertrouwelijkheidaanduiding not in grouped_by_va:
            grouped_by_va[spec.max_vertrouwelijkheidaanduiding] = []

        if (
            catalogus_autorisaties
            and catalogus_autorisaties[0].max_vertrouwelijkheidaanduiding
            not in grouped_by_va
        ):
            grouped_by_va[catalogus_autorisaties[0].max_vertrouwelijkheidaanduiding] = (
                []
            )

        for va, _autorisaties in grouped_by_va.items():
            _initial = {"vertrouwelijkheidaanduiding": va}
            relevant_ids = {
                related_objs[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in related_objs
            }
            relevant_external = [
                _related_objs_external[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in _related_objs_external
            ]

            if spec:
                _initial["related_type_selection"] = (
                    RelatedTypeSelectionMethods.all_current_and_future
                )
            elif informatieobjecttype_ids == relevant_ids:
                _initial["related_type_selection"] = (
                    RelatedTypeSelectionMethods.all_current
                )
            elif catalogus_autorisaties:
                _initial.update(
                    {
                        "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                        "catalogi": [
                            catalogus_autorisatie.catalogus.pk
                            for catalogus_autorisatie in catalogus_autorisaties
                        ],
                    }
                )
            else:
                _initial.update(
                    {
                        "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                        "informatieobjecttypen": relevant_ids,
                        "externe_typen": relevant_external,
                    }
                )
            initial.append(_initial)

    elif component == ComponentTypes.brc:
        besluittype_ids = set(BesluitType.objects.values_list("id", flat=True))
        relevant_ids = set(related_objs.values())

        _initial = {"externe_typen": _related_objs_external}

        if spec:
            _initial["related_type_selection"] = (
                RelatedTypeSelectionMethods.all_current_and_future
            )
        elif besluittype_ids == relevant_ids:
            _initial["related_type_selection"] = RelatedTypeSelectionMethods.all_current
        elif catalogus_autorisaties:
            _initial.update(
                {
                    "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                    "catalogi": [
                        catalogus_autorisatie.catalogus.pk
                        for catalogus_autorisatie in catalogus_autorisaties
                    ],
                }
            )
        else:
            _initial.update(
                {
                    "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                    "besluittypen": relevant_ids,
                }
            )
        initial.append(_initial)
    else:
        # The other components do not have any extra options
        initial.append({})

    return initial


def _get_group_key(
    spec: Union[Autorisatie, AutorisatieSpec, CatalogusAutorisatie]
) -> Tuple[str, Tuple[str]]:
    return (spec.component, tuple(sorted(spec.scopes)))


def get_initial(applicatie: Applicatie) -> List[Dict[str, Any]]:
    """
    Figure out the initial data for the formset, showing existing config.

    We group applicatie autorisaties bij (component, scopes) and evaluate
    if this constitutes one of the "special" options. If so, we can provide
    this information to the form, presenting it much more condensed to the
    end user.
    """
    initial = []

    autorisatie_specs = {
        (spec.component, tuple(sorted(spec.scopes))): spec
        for spec in applicatie.autorisatie_specs.all()
    }

    catalogus_autorisaties = defaultdict(list)
    for catalogus_autorisatie in applicatie.catalogusautorisatie_set.all():
        catalogus_autorisaties[
            (
                catalogus_autorisatie.component,
                tuple(sorted(catalogus_autorisatie.scopes)),
            )
        ].append(catalogus_autorisatie)

    grouped = defaultdict(list)
    autorisaties = applicatie.autorisaties.all()
    for autorisatie in autorisaties:
        key = _get_group_key(autorisatie)
        grouped[key].append(autorisatie)

    # if there's no existing records yet, there will not be any autorisaties and we
    # have to inject the autorisatiespec itself. See #1080 for the bug report.
    for spec in autorisatie_specs.values():
        key = _get_group_key(spec)
        # can happen if there's a spec but no existing records yet
        if key in grouped:
            continue
        grouped[key] = []

    # if there's no existing records yet, there will not be any autorisaties and we
    # have to inject the autorisatiespec itself. See #1080 for the bug report.
    for catalogus_autorisatie in catalogus_autorisaties.values():
        key = _get_group_key(catalogus_autorisatie[0])
        # can happen if there's a spec but no existing records yet
        if key in grouped:
            continue
        grouped[key] = []

    for (component, _scopes), _autorisaties in grouped.items():
        component_initial = get_initial_for_component(
            component,
            _autorisaties,
            autorisatie_specs.get((component, _scopes)),
            catalogus_autorisaties.get((component, _scopes)),
        )
        initial += [
            {"component": component, "scopes": list(_scopes), **_initial}
            for _initial in component_initial
        ]

    return initial


class AutorisatiesView(AdminContextMixin, DetailView):
    model = Applicatie
    template_name = "admin/autorisaties/applicatie_autorisaties.html"
    pk_url_kwarg = "object_id"
    # set these on the .as_view(...) call
    admin_site = None
    model_admin = None

    # perform permission checks
    def dispatch(self, request, *args, **kwargs):
        assert self.admin_site
        assert self.model_admin

        applicatie = self.get_object()
        if not self.model_admin.has_change_permission(request, applicatie):
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = applicatie = self.get_object()
        formset = self.get_formset()

        if formset.is_valid():
            formset.save()
            return redirect(
                "admin:authorizations_applicatie_change", object_id=applicatie.pk
            )

        context = self.get_context_data(formset=formset)
        return self.render_to_response(context)

    def get_formset(self):
        initial = get_initial(self.object)
        data = self.request.POST if self.request.method == "POST" else None
        return AutorisatieFormSet(
            data=data, initial=initial, applicatie=self.object, request=self.request
        )

    def get_context_data(self, **kwargs):
        formset = kwargs.pop("formset", self.get_formset())
        kwargs["formset"] = formset

        context = super().get_context_data(**kwargs)

        catalogi = Catalogus.objects.prefetch_related(
            "zaaktype_set",
            "informatieobjecttype_set",
            "besluittype_set",
        )

        context.update(
            {
                "opts": Applicatie._meta,
                "original": self.get_object(),
                "title": _("beheer autorisaties"),
                "is_popup": False,
                "formset_config": {
                    "prefix": formset.prefix,
                    "extra": formset.extra,
                    **{
                        field.name: int(field.value())
                        for field in formset.management_form
                    },
                },
                "scope_choices": get_scope_choices(),
                "COMPONENTS_TO_PREFIXES_MAP": COMPONENT_TO_PREFIXES_MAP,
                "RELATED_TYPE_SELECTION_METHODS": RelatedTypeSelectionMethods.choices,
                "VA_CHOICES": VertrouwelijkheidsAanduiding.choices,
                "catalogi": CatalogusSerializer(
                    catalogi, read_only=True, many=True
                ).data,
                "formdata": [get_form_data(form) for form in formset],
            }
        )

        return context
