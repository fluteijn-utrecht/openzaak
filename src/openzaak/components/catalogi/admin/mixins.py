import uuid
from datetime import date
from urllib.parse import parse_qsl, quote as urlquote

from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.management import CommandError, call_command
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import ExtraContextAdminMixin

from ..models import Catalogus, ZaakType
from .forms import CatalogusImportForm


class GeldigheidAdminMixin(object):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return tuple(fieldsets) + (
            (
                _("Geldigheid"),
                {"fields": ("datum_begin_geldigheid", "datum_einde_geldigheid")},
            ),
        )


class ConceptAdminMixin(object):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return tuple(fieldsets) + ((_("Concept"), {"fields": ("concept",)}),)


class PublishAdminMixin:
    def _publish_validation_errors(self, obj):
        return []

    def response_post_save_change(self, request, obj):
        if "_publish" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            errors = self._publish_validation_errors(obj)
            if errors:
                for error in errors:
                    self.message_user(request, error, level=messages.ERROR)
            else:
                obj.concept = False
                obj.save()
                msg = _("The resource has been published successfully!")
                self.message_user(request, msg, level=messages.SUCCESS)

            return HttpResponseRedirect(request.path)
        else:
            return super().response_post_save_change(request, obj)

    def is_published(self, obj):
        """
        Helper to show publish status in admin list views.

        :param obj: The model instance.
        :return: `True` if the instance was published.
        """
        return not obj.concept

    is_published.short_description = _("gepubliceerd")
    is_published.boolean = True


class NewVersionMixin(object):
    exclude_copy_relation = []

    def create_new_version(self, obj):
        old_pk = obj.pk

        # new obj
        version_date = date.today()

        obj.pk = None
        obj.uuid = uuid.uuid4()
        obj.datum_begin_geldigheid = obj.datum_einde_geldigheid
        obj.versiedatum = version_date
        obj.datum_einde_geldigheid = None
        obj.concept = True
        obj.save()

        related_objects = [
            f
            for f in obj._meta.get_fields(include_hidden=True)
            if (f.auto_created and not f.concrete)
        ]

        # related objects
        for relation in related_objects:
            if relation.name in self.exclude_copy_relation:
                continue

            # m2m relation included in the loop below as one_to_many
            if relation.one_to_many or relation.one_to_one:
                remote_model = relation.related_model
                remote_field = relation.field.name

                related_queryset = remote_model.objects.filter(**{remote_field: old_pk})
                for related_obj in related_queryset:
                    related_obj.pk = None
                    setattr(related_obj, remote_field, obj)

                    if hasattr(related_obj, "uuid"):
                        related_obj.uuid = uuid.uuid4()
                    related_obj.save()

    def response_change(self, request, obj):
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)
        msg_dict = {
            "name": opts.verbose_name,
            "obj": format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        if "_addversion" in request.POST:
            self.create_new_version(obj)

            msg = format_html(
                _('The new version of {name} "{obj}" was successfully created'),
                **msg_dict,
            )
            self.message_user(request, msg, messages.SUCCESS)

            redirect_url = reverse(
                "admin:%s_%s_change" % (opts.app_label, opts.model_name),
                args=(obj.pk,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {"preserved_filters": preserved_filters, "opts": opts}, redirect_url
            )
            return HttpResponseRedirect(redirect_url)

        return super().response_change(request, obj)


class ExportMixin:
    resource_name = ""

    def get_related_objects(self, obj):
        """
        Must be implemented to retrieve the objects that have to be exported
        along with the main object
        """
        return [], []

    def response_post_save_change(self, request, obj):
        if "_export" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            resource_list, id_list = self.get_related_objects(obj)

            response = HttpResponse(content_type="application/zip")
            filename = slugify(str(obj))
            response["Content-Disposition"] = "attachment;filename={}".format(
                f"{filename}.zip"
            )
            call_command(
                "export", response=response, resource=resource_list, ids=id_list,
            )

            response["Content-Length"] = len(response.content)

            self.message_user(
                request,
                _("{} {} was successfully exported").format(
                    self.resource_name.capitalize(), obj
                ),
                level=messages.SUCCESS,
            )
            return response
        else:
            return super().response_post_save_change(request, obj)


class CatalogusContextAdminMixin(ExtraContextAdminMixin):
    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)

        zaaktype = None
        catalogus = None

        _changelist_filters = dict(parse_qsl(request.GET.get("_changelist_filters")))
        zaaktype_pk = _changelist_filters.get(
            "zaaktype__id__exact", request.GET.get("zaaktype__id__exact")
        )
        catalogus_pk = _changelist_filters.get(
            "catalogus__id__exact", request.GET.get("catalogus__id__exact")
        )

        if zaaktype_pk:
            zaaktype = (
                ZaakType.objects.select_related("catalogus")
                .filter(pk=int(zaaktype_pk))
                .first()
            )
            catalogus = zaaktype.catalogus
        elif catalogus_pk:
            catalogus = Catalogus.objects.get(pk=int(catalogus_pk))

        context.update(
            {"zaaktype": zaaktype, "catalogus": catalogus,}
        )

        return context


class ImportMixin:
    resource_name = ""

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name=f"catalogi_{self.resource_name}_import",
            )
        ]
        return my_urls + urls

    def import_view(self, request):
        form = CatalogusImportForm(request.POST, request.FILES)
        context = dict(self.admin_site.each_context(request), form=form)
        if "_import" in request.POST:
            form = CatalogusImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    import_file = form.cleaned_data["file"]
                    generate_new_uuids = form.cleaned_data["generate_new_uuids"]
                    call_command(
                        "import",
                        import_file_content=import_file.read(),
                        generate_new_uuids=generate_new_uuids,
                    )
                    self.message_user(
                        request,
                        _("Catalogus successfully imported"),
                        level=messages.SUCCESS,
                    )
                    return HttpResponseRedirect(
                        reverse("admin:catalogi_catalogus_changelist")
                    )
                except CommandError as exc:
                    self.message_user(request, exc, level=messages.ERROR)
        else:
            form = CatalogusImportForm()

        context = dict(self.admin_site.each_context(request), form=form)

        return TemplateResponse(
            request, "admin/catalogi/import_catalogus.html", context
        )
