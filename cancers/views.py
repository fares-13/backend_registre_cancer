from rest_framework import viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from .models import CancerCase, Anapath, Imaging, Analysis, CancerType, CancerAttribute, CancerTreatment
from .serializers import (
    CancerCaseSerializer, AnapathSerializer, 
    ImagingSerializer, AnalysisSerializer,
    CancerTypeSerializer, CancerAttributeSerializer,
    CancerTreatmentSerializer
)
from accounts.permissions import IsAdmin, IsArchitect, IsMedecin

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

class CancerCaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Cancer Cases. 
    Supports nested creation of Anapath, Imagings, and Analyses.
    """
    queryset = CancerCase.objects.all().order_by('-created_at')
    serializer_class = CancerCaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset

class AnapathViewSet(viewsets.ModelViewSet):
    queryset = Anapath.objects.all()
    serializer_class = AnapathSerializer
    permission_classes = [permissions.IsAuthenticated]

class ImagingViewSet(viewsets.ModelViewSet):
    queryset = Imaging.objects.all()
    serializer_class = ImagingSerializer
    permission_classes = [permissions.IsAuthenticated]

class AnalysisViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Analyses. 
    Supports file uploads via MultiPartParser.
    """
    queryset = Analysis.objects.all()
    serializer_class = AnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        # Allow creating analysis by passing cancer_case ID in the form data
        return super().create(request, *args, **kwargs)

class CancerTreatmentViewSet(viewsets.ModelViewSet):
    queryset = CancerTreatment.objects.all()
    serializer_class = CancerTreatmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # You can add custom logic here if needed, like setting the doctor
        serializer.save()
