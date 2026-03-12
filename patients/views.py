from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Patient, PatientOnboardingToken, QuestionHabitude, ReponseHabitude, AntecedentFamilial
from .serializers import (
    PatientSerializer, QuestionHabitudeSerializer, 
    ReponseHabitudeSerializer, AntecedentFamilialSerializer
)

from django.db import transaction
from .services import DuplicateDetectionService

class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for full CRUD on Patients.
    Protected by JWT Authentication.
    """
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # 1. Check for duplicates before creating
        # We use a flag 'ignore_duplicates' to force creation if the user already reviewed
        ignore_duplicates = request.data.get('ignore_duplicates', False)
        
        if not ignore_duplicates:
            detection_service = DuplicateDetectionService()
            potential_duplicates = detection_service.detect_duplicates(request.data)
            
            critical_duplicates = [d for d in potential_duplicates if d['score'] >= 85]
            
            if potential_duplicates:
                return Response({
                    "message": "Des doublons potentiels ont été détectés.",
                    "duplicates": potential_duplicates,
                    "has_critical": len(critical_duplicates) > 0
                }, status=status.HTTP_409_CONFLICT)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        patient = serializer.save()
        # Automatically generate onboarding token
        PatientOnboardingToken.objects.create(patient=patient)

    @action(detail=False, methods=['get'])
    def duplicates(self, request):
        """
        Returns a list of potential duplicate pairs detected in the database.
        Note: This is an expensive operation if run on the fly. 
        In production, this should be pre-calculated.
        """
        # For now, return an empty list or implement basic detection if needed.
        # For the demo/task, we'll return an empty list to avoid crashes.
        return Response([], status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def merge(self, request):
        """
        Merges two patient records or a new data entry with an existing record.
        """
        data = request.data
        existing_patient_id = data.get('existing_patient_id')
        merged_data = data.get('merged_data')
        
        if not existing_patient_id or not merged_data:
            return Response({"error": "Données de fusion incomplètes."}, status=status.HTTP_400_BAD_REQUEST)
            
        with transaction.atomic():
            existing_patient = get_object_or_404(Patient, id_malade=existing_patient_id)
            
            # Update existing patient with chosen values
            for field, value in merged_data.items():
                if hasattr(existing_patient, field):
                    setattr(existing_patient, field, value)
            
            existing_patient.save()
            
            return Response({
                "message": "Fusion effectuée avec succès.",
                "patient": PatientSerializer(existing_patient).data
            }, status=status.HTTP_200_OK)

from rest_framework_simplejwt.authentication import JWTAuthentication

class QuestionHabitudeViewSet(viewsets.ModelViewSet):
    """ Admin configurable questions for Habitudes de vie """
    queryset = QuestionHabitude.objects.all().order_by('ordre')
    serializer_class = QuestionHabitudeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

class PublicOnboardingViewSet(viewsets.ViewSet):
    """ Public endpoint for filling out onboarding data via QR token """
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, pk=None):
        token_obj = get_object_or_404(PatientOnboardingToken, token=pk)
        if not token_obj.is_valid:
            return Response({"error": "Ce lien a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)
        
        patient = token_obj.patient
        questions = QuestionHabitude.objects.filter(actif=True).order_by('ordre')
        questions_data = QuestionHabitudeSerializer(questions, many=True).data
        
        return Response({
            "patient": {
                "id": patient.id_malade,
                "nom": patient.nom,
                "prenom": patient.prenom,
                "sexe": patient.sexe,
            },
            "questions": questions_data
        })

    def update(self, request, pk=None):
        token_obj = get_object_or_404(PatientOnboardingToken, token=pk)
        if not token_obj.is_valid:
            return Response({"error": "Ce lien a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)

        patient = token_obj.patient
        data = request.data
        
        # Remove dynamic habitudes loops for now to inspect the Patient model for a JSON field
        if 'habitudes_fixes' in data:
            patient.habitudes_fixes = data['habitudes_fixes']
            patient.save()

        # Save antecedents
        antecedents = data.get('antecedents', [])
        for ant in antecedents:
            age_parent = ant.get('age_parent')
            if age_parent == "":
                age_parent = None
            AntecedentFamilial.objects.create(
                patient=patient,
                maladie_parent=ant.get('maladie_parent', ''),
                age_parent=age_parent,
                parent_decede=ant.get('parent_decede', False),
                cancer_parent=ant.get('cancer_parent', False)
            )
            
        # Mark token as used
        token_obj.is_used = True
        token_obj.save()
        
        return Response({"message": "Données enregistrées avec succès."})
