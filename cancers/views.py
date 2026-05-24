from rest_framework import viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .models import (
    CancerCase, Anapath, Imaging, Analysis, CancerType,
    CancerAttribute, CancerTreatment, ImagingType, AnalysisType,
    MolecularMarker, FollowUp
)

from .serializers import (
    CancerCaseSerializer, CancerCaseListSerializer, AnapathSerializer,
    ImagingSerializer, AnalysisSerializer,
    CancerTypeSerializer, CancerAttributeSerializer,
    CancerTreatmentSerializer, ImagingTypeSerializer, AnalysisTypeSerializer,
    MolecularMarkerSerializer, FollowUpSerializer
)

from accounts.permissions import IsAdmin, IsArchitect, IsMedecin

from audit.helpers import log_action
from audit.models import AuditLog


class CancerTypeViewSet(viewsets.ModelViewSet):
    queryset = CancerType.objects.all().order_by('nom')
    serializer_class = CancerTypeSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsArchitect()]
        return [permissions.IsAuthenticated()]


class CancerAttributeViewSet(viewsets.ModelViewSet):
    queryset = CancerAttribute.objects.all()
    serializer_class = CancerAttributeSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsArchitect()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        cancer_type_id = self.request.query_params.get('cancer_type')
        is_active = self.request.query_params.get('is_active')

        if cancer_type_id:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(cancer_type_id=cancer_type_id) |
                Q(is_basic=True)
            )
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class ImagingTypeViewSet(viewsets.ModelViewSet):
    queryset = ImagingType.objects.all().order_by('nom')
    serializer_class = ImagingTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        cancer_type_id = self.request.query_params.get('cancer_type')
        if cancer_type_id:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(cancer_type_id=cancer_type_id) |
                Q(cancer_type__isnull=True)
            )
        return queryset


class AnalysisTypeViewSet(viewsets.ModelViewSet):
    queryset = AnalysisType.objects.all().order_by('nom')
    serializer_class = AnalysisTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        cancer_type_id = self.request.query_params.get('cancer_type')
        if cancer_type_id:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(cancer_type_id=cancer_type_id) |
                Q(cancer_type__isnull=True)
            )
        return queryset


class CancerCaseViewSet(viewsets.ModelViewSet):

    queryset = CancerCase.objects.all().select_related(
        'patient',
        'cancer_type'
    ).prefetch_related(
        'anapath',
        'imagings',
        'analyses',
        'treatments'
    ).order_by('-created_at')

    serializer_class = CancerCaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return CancerCaseListSerializer
        return CancerCaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get('patient_id')
        search = self.request.query_params.get('search', '').strip()

        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(type_cancer__icontains=search) |
                Q(sous_type__icontains=search) |
                Q(patient__nom__icontains=search) |
                Q(patient__prenom__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        case = serializer.save()
        patient = case.patient
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.CREATE_CASE,
            entity_type=AuditLog.EntityType.CANCER_CASE,
            entity_id=str(case.id_cancer),
            entity_label=f"Cas cancer - {patient.nom} {patient.prenom}",
            description=f"Création d'un cas cancer pour {patient.nom} {patient.prenom}",
            request=self.request,
        )

    def perform_update(self, serializer):
        case = serializer.save()
        patient = case.patient
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.UPDATE_CASE,
            entity_type=AuditLog.EntityType.CANCER_CASE,
            entity_id=str(case.id_cancer),
            entity_label=f"Cas cancer - {patient.nom} {patient.prenom}",
            description=f"Modification du cas cancer de {patient.nom} {patient.prenom}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        patient = instance.patient
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.DELETE_CASE,
            entity_type=AuditLog.EntityType.CANCER_CASE,
            entity_id=str(instance.id_cancer),
            entity_label=f"Cas cancer - {patient.nom} {patient.prenom}",
            description=f"Suppression du cas cancer de {patient.nom} {patient.prenom}",
            request=self.request,
        )
        instance.delete()


class AnapathViewSet(viewsets.ModelViewSet):
    queryset = Anapath.objects.all()
    serializer_class = AnapathSerializer
    permission_classes = [permissions.IsAuthenticated]


# =========================
# IMAGING VIEWSET
# =========================

class ImagingViewSet(viewsets.ModelViewSet):
    queryset = Imaging.objects.all()
    serializer_class = ImagingSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        imaging = serializer.save()
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.UPLOAD_DOCUMENT,
            entity_type=AuditLog.EntityType.DOCUMENT,
            entity_id=str(imaging.id_imagerie),
            entity_label=f"Imagerie: {imaging.type_imagerie or 'Document'}",
            description=f"Upload d'un document d'imagerie",
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.DELETE_DOCUMENT,
            entity_type=AuditLog.EntityType.DOCUMENT,
            entity_id=str(instance.id_imagerie),
            entity_label=f"Imagerie: {instance.type_imagerie or 'Document'}",
            description=f"Suppression d'un document d'imagerie",
            request=self.request,
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        print("\n========== IMAGING DEBUG ==========")
        print("FILES:", request.FILES)
        print("DATA:", request.data)
        print("===================================\n")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("\nIMAGING SERIALIZER ERRORS:")
            print(serializer.errors)
            print("\n")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =========================
# ANALYSIS VIEWSET
# =========================

class AnalysisViewSet(viewsets.ModelViewSet):

    queryset = Analysis.objects.all()
    serializer_class = AnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        analysis = serializer.save()
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.UPLOAD_DOCUMENT,
            entity_type=AuditLog.EntityType.DOCUMENT,
            entity_id=str(analysis.id_analyse),
            entity_label=f"Analyse: {analysis.type_analyse or 'Document'}",
            description=f"Upload d'un document d'analyse",
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.DELETE_DOCUMENT,
            entity_type=AuditLog.EntityType.DOCUMENT,
            entity_id=str(instance.id_analyse),
            entity_label=f"Analyse: {instance.type_analyse or 'Document'}",
            description=f"Suppression d'un document d'analyse",
            request=self.request,
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        print("\n========== ANALYSIS DEBUG ==========")
        print("FILES:", request.FILES)
        print("DATA:", request.data)
        print("====================================\n")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("\nANALYSIS SERIALIZER ERRORS:")
            print(serializer.errors)
            print("\n")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CancerTreatmentViewSet(viewsets.ModelViewSet):
    queryset = CancerTreatment.objects.all()
    serializer_class = CancerTreatmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        treatment = serializer.save()
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.ADD_TREATMENT,
            entity_type=AuditLog.EntityType.TREATMENT,
            entity_id=str(treatment.id_traitement),
            entity_label=f"Traitement: {treatment.type_traitement or 'Traitement'}",
            description=f"Ajout d'un traitement: {treatment.type_traitement}",
            request=self.request,
        )

    def perform_update(self, serializer):
        treatment = serializer.save()
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.UPDATE_TREATMENT,
            entity_type=AuditLog.EntityType.TREATMENT,
            entity_id=str(treatment.id_traitement),
            entity_label=f"Traitement: {treatment.type_traitement or 'Traitement'}",
            description=f"Modification du traitement: {treatment.type_traitement}",
            request=self.request,
        )


class MolecularMarkerViewSet(viewsets.ModelViewSet):
    queryset = MolecularMarker.objects.all()
    serializer_class = MolecularMarkerSerializer
    permission_classes = [permissions.IsAuthenticated]


class FollowUpViewSet(viewsets.ModelViewSet):
    queryset = FollowUp.objects.all()
    serializer_class = FollowUpSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        followup = serializer.save()
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.ADD_FOLLOWUP,
            entity_type=AuditLog.EntityType.FOLLOWUP,
            entity_id=str(followup.id_followup),
            entity_label=f"Suivi - {followup.visit_type or 'Consultation'}",
            description=f"Ajout d'un suivi: {followup.visit_type or 'Consultation'}",
            request=self.request,
        )

    def perform_update(self, serializer):
        followup = serializer.save()
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.MODIFY_FOLLOWUP,
            entity_type=AuditLog.EntityType.FOLLOWUP,
            entity_id=str(followup.id_followup),
            entity_label=f"Suivi - {followup.visit_type or 'Consultation'}",
            description=f"Modification du suivi: {followup.visit_type or 'Consultation'}",
            request=self.request,
        )
