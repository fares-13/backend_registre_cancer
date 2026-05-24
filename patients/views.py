from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Patient, PatientOnboardingToken, QuestionHabitude, ReponseHabitude, AntecedentFamilial
from .serializers import (
    PatientSerializer, QuestionHabitudeSerializer,
    ReponseHabitudeSerializer, AntecedentFamilialSerializer
)

from django.db import transaction
from .services import DuplicateDetectionService

from audit.helpers import log_action
from audit.models import AuditLog

from services.ai.patient_extraction import (
    extract_patient_from_transcript,
    PatientExtractionError,
    AIProviderNotAvailableError,
    InvalidJSONError,
    EmptyResponseError,
)


class ExtractPatientAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        transcript = str(request.data.get("transcript", "")).strip()
        if not transcript:
            return Response(
                {"detail": "Le champ transcript est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            extracted = extract_patient_from_transcript(transcript)
        except AIProviderNotAvailableError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except InvalidJSONError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except EmptyResponseError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except PatientExtractionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Erreur extraction: {str(exc)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(extracted, status=status.HTTP_200_OK)


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for full CRUD on Patients.
    Supports server-side search, filtering, and pagination.
    Protected by JWT Authentication.
    """
    queryset = Patient.objects.all().prefetch_related(
        'habitudes_reponses',
        'antecedents_familiaux',
    ).order_by('-created_at')
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search', '').strip()
        sexe = self.request.query_params.get('sexe', '').strip()
        deces = self.request.query_params.get('deces', '').strip()

        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(nom__icontains=search) |
                Q(prenom__icontains=search) |
                Q(numero_dossier__icontains=search) |
                Q(N_securite_sociale__icontains=search) |
                Q(N_carte_nationale__icontains=search)
            )
        if sexe:
            qs = qs.filter(sexe=sexe)
        if deces:
            qs = qs.filter(deces=deces.lower() == 'true')

        return qs

    def create(self, request, *args, **kwargs):
        """
        Create a patient, with duplicate detection before saving.
        """
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
        PatientOnboardingToken.objects.create(patient=patient)
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.CREATE_PATIENT,
            entity_type=AuditLog.EntityType.PATIENT,
            entity_id=str(patient.id_malade),
            entity_label=f"{patient.nom} {patient.prenom}",
            description=f"Création du patient {patient.nom} {patient.prenom}",
            request=self.request,
        )

    def perform_update(self, serializer):
        patient = serializer.save()
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.UPDATE_PATIENT,
            entity_type=AuditLog.EntityType.PATIENT,
            entity_id=str(patient.id_malade),
            entity_label=f"{patient.nom} {patient.prenom}",
            description=f"Modification du patient {patient.nom} {patient.prenom}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.DELETE_PATIENT,
            entity_type=AuditLog.EntityType.PATIENT,
            entity_id=str(instance.id_malade),
            entity_label=f"{instance.nom} {instance.prenom}",
            description=f"Suppression du patient {instance.nom} {instance.prenom}",
            request=self.request,
        )
        instance.delete()

    @action(detail=False, methods=['post'], url_path='check-duplicate')
    def check_duplicate(self, request):
        """Check for duplicates without creating a patient."""
        detection_service = DuplicateDetectionService()
        potential_duplicates = detection_service.detect_duplicates(request.data)
        critical = [d for d in potential_duplicates if d['score'] >= 85]
        return Response({
            "duplicates": potential_duplicates,
            "has_duplicates": len(potential_duplicates) > 0,
            "has_critical": len(critical) > 0,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def duplicates(self, request):
        """Scans DB for duplicate patient pairs."""
        min_score = int(request.query_params.get('min_score', 75))
        limit = int(request.query_params.get('limit', 50))
        patients_sample = Patient.objects.all().order_by('-created_at')[:500]
        found_pairs = []
        seen = set()
        detection_service = DuplicateDetectionService()

        for patient in patients_sample:
            if len(found_pairs) >= limit:
                break
            patient_data = {
                'nom': patient.nom,
                'prenom': patient.prenom,
                'date_naissance': patient.date_naissance.isoformat() if patient.date_naissance else None,
                'sexe': patient.sexe,
                'N_carte_nationale': patient.N_carte_nationale,
                'telephone': patient.telephone,
            }
            duplicates_for_patient = detection_service.detect_duplicates(patient_data)

            for dup in duplicates_for_patient:
                if str(dup['id_malade']) == str(patient.id_malade):
                    continue
                pair_key = tuple(sorted([str(patient.id_malade), str(dup['id_malade'])]))
                if pair_key in seen:
                    continue
                if dup['score'] >= min_score:
                    seen.add(pair_key)
                    found_pairs.append({
                        'patient_1': {
                            'id': str(patient.id_malade),
                            'nom': patient.nom,
                            'prenom': patient.prenom,
                            'date_naissance': patient_data['date_naissance'],
                        },
                        'patient_2': dup,
                        'score': dup['score'],
                    })

        found_pairs.sort(key=lambda x: x['score'], reverse=True)
        return Response({
            'count': len(found_pairs),
            'pairs': found_pairs,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def merge(self, request):
        """Merges two patient records."""
        data = request.data
        existing_patient_id = data.get('existing_patient_id')
        merged_data = data.get('merged_data')

        if not existing_patient_id or not merged_data:
            return Response({"error": "Données de fusion incomplètes."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            existing_patient = get_object_or_404(Patient, id_malade=existing_patient_id)
            for field, value in merged_data.items():
                if hasattr(existing_patient, field):
                    setattr(existing_patient, field, value)
            existing_patient.save()

            log_action(
                user=self.request.user,
                action_type=AuditLog.ActionType.DUPLICATE_PATIENT,
                entity_type=AuditLog.EntityType.PATIENT,
                entity_id=str(existing_patient.id_malade),
                entity_label=f"{existing_patient.nom} {existing_patient.prenom}",
                description=f"Fusion de doublons vers le patient {existing_patient.nom} {existing_patient.prenom}",
                request=self.request,
                metadata={"merged_fields": list(merged_data.keys())},
            )

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

        if 'habitudes_fixes' in data:
            patient.habitudes_fixes = data['habitudes_fixes']
            patient.save()

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

        token_obj.is_used = True
        token_obj.save()

        return Response({"message": "Données enregistrées avec succès."})
