from django.contrib import admin
from .models import (
    CancerType,
    CancerAttribute,
    ImagingType,
    AnalysisType,
    CancerCase,
    Anapath,
    Imaging,
    Analysis,
    CancerTreatment,
    MolecularMarker,
    FollowUp,
)


# =========================
# INLINE ATTRIBUTES
# =========================

class CancerAttributeInline(admin.TabularInline):
    model = CancerAttribute
    extra = 1

    fields = (
        "label",
        "nom_interne",
        "field_type",
        "requis",
        "is_basic",
        "is_active",
    )


# =========================
# CANCER TYPE ADMIN
# =========================

@admin.register(CancerType)
class CancerTypeAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "description",
        "created_at",
    )

    search_fields = (
        "nom",
        "description",
    )

    inlines = [CancerAttributeInline]

    ordering = ("nom",)


# =========================
# CANCER ATTRIBUTE ADMIN
# =========================

@admin.register(CancerAttribute)
class CancerAttributeAdmin(admin.ModelAdmin):

    list_display = (
        "label",
        "nom_interne",
        "cancer_type",
        "field_type",
        "requis",
        "is_basic",
        "is_active",
    )

    list_filter = (
        "field_type",
        "is_basic",
        "is_active",
    )

    search_fields = (
        "label",
        "nom_interne",
    )

    ordering = ("label",)


# =========================
# IMAGING TYPE ADMIN
# =========================

@admin.register(ImagingType)
class ImagingTypeAdmin(admin.ModelAdmin):

    list_display = (
        "nom",
        "cancer_type",
    )

    search_fields = (
        "nom",
    )


# =========================
# ANALYSIS TYPE ADMIN
# =========================

@admin.register(AnalysisType)
class AnalysisTypeAdmin(admin.ModelAdmin):

    list_display = (
        "nom",
        "cancer_type",
    )

    search_fields = (
        "nom",
    )


# =========================
# CANCER CASE ADMIN
# =========================

@admin.register(CancerCase)
class CancerCaseAdmin(admin.ModelAdmin):

    list_display = (
        "patient",
        "cancer_type",
        "etat",
        "date_diagnostic",
        "created_at",
    )

    search_fields = (
        "patient__nom",
        "patient__prenom",
        "type_cancer",
    )

    list_filter = (
        "etat",
        "cancer_type",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


# =========================
# ANAPATH ADMIN
# =========================

@admin.register(Anapath)
class AnapathAdmin(admin.ModelAdmin):

    list_display = (
        "N_dossier_anapath",
        "cancer_case",
        "date_etude",
    )

    search_fields = (
        "N_dossier_anapath",
    )


# =========================
# IMAGING ADMIN
# =========================

@admin.register(Imaging)
class ImagingAdmin(admin.ModelAdmin):

    list_display = (
        "type_imagerie",
        "cancer_case",
        "date_imagerie",
    )

    search_fields = (
        "type_imagerie",
    )


# =========================
# ANALYSIS ADMIN
# =========================

@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):

    list_display = (
        "type_analyse",
        "cancer_case",
        "date_analyse",
    )

    search_fields = (
        "type_analyse",
    )


# =========================
# TREATMENT ADMIN
# =========================

@admin.register(CancerTreatment)
class CancerTreatmentAdmin(admin.ModelAdmin):

    list_display = (
        "type_traitement",
        "cancer_case",
        "date_traitement",
    )

    search_fields = (
        "type_traitement",
    )


# =========================
# MOLECULAR MARKER ADMIN
# =========================

@admin.register(MolecularMarker)
class MolecularMarkerAdmin(admin.ModelAdmin):

    list_display = (
        "marker_name",
        "cancer_case",
        "result",
        "test_date",
    )

    search_fields = (
        "marker_name",
    )

    list_filter = (
        "marker_name",
    )


# =========================
# FOLLOW-UP ADMIN
# =========================

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):

    list_display = (
        "visit_type",
        "cancer_case",
        "visit_date",
        "next_visit_date",
    )

    search_fields = (
        "visit_type",
    )

    list_filter = (
        "visit_type",
    )