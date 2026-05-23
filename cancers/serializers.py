from rest_framework import serializers
from django.db import transaction
from .models import (
    CancerCase, Anapath, Imaging, Analysis, CancerType,
    CancerAttribute, CancerTreatment, ImagingType, AnalysisType,
    MolecularMarker, FollowUp
)
from patients.serializers import PatientSerializer
from patients.models import Patient

class CancerAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancerAttribute
        fields = ['id_attribute', 'cancer_type', 'nom_interne', 'label', 'field_type', 'requis', 'options', 'is_basic', 'is_active']

class ImagingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagingType
        fields = '__all__'

class AnalysisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisType
        fields = '__all__'

class CancerTypeSerializer(serializers.ModelSerializer):
    attributes = CancerAttributeSerializer(many=True, read_only=True)
    
    class Meta:
        model = CancerType
        fields = ['id_type', 'nom', 'description', 'attributes', 'created_at', 'updated_at']

class AnapathSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anapath
        fields = ['id_anapath', 'cancer_case', 'N_dossier_anapath', 'N_lecture', 'medecin', 'date_etude', 'report']
        extra_kwargs = {'cancer_case': {'read_only': True, 'required': False}}

class ImagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imaging
        fields = [
            'id_imagerie',
            'cancer_case',
            'type_imagerie',
            'date_imagerie',
            'document'
        ]


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = [
            'id_analyse',
            'cancer_case',
            'type_analyse',
            'date_analyse',
            'document'
        ]
class CancerTreatmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancerTreatment
        fields = ['id_traitement', 'cancer_case', 'type_traitement', 'date_traitement', 'remarques', 'created_at']


class MolecularMarkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MolecularMarker
        fields = '__all__'
        extra_kwargs = {'cancer_case': {'read_only': True, 'required': False}}

class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = '__all__'
        extra_kwargs = {'cancer_case': {'read_only': True, 'required': False}}

class CancerCaseListSerializer(serializers.ModelSerializer):

    patient_nom = serializers.CharField(source='patient.nom', read_only=True)
    patient_prenom = serializers.CharField(source='patient.prenom', read_only=True)
    cancer_type_nom = serializers.SerializerMethodField()

    # Add lightweight nested docs
    imagings = ImagingSerializer(many=True, read_only=True)
    analyses = AnalysisSerializer(many=True, read_only=True)
    anapath = AnapathSerializer(read_only=True)

    class Meta:
        model = CancerCase
        fields = [
            'id_cancer',
            'patient_nom',
            'patient_prenom',
            'cancer_type_nom',
            'type_cancer',
            'sous_type',
            'etat',
            'date_diagnostic',
            'created_at',

            # Needed for Patient Documents page
            'imagings',
            'analyses',
            'anapath',
        ]

    def get_cancer_type_nom(self, obj):
        return obj.cancer_type.nom if obj.cancer_type else None

class CancerCaseSerializer(serializers.ModelSerializer):
    anapath = AnapathSerializer(required=False, allow_null=True)
    imagings = ImagingSerializer(many=True, required=False)
    analyses = AnalysisSerializer(many=True, required=False)
    treatments = CancerTreatmentSerializer(many=True, required=False)
    
    # Type de cancer detail
    cancer_type_detail = CancerTypeSerializer(source='cancer_type', read_only=True)
    
    # Read-only patient details for GET requests
    patient = PatientSerializer(read_only=True)
    
    # Writable fields
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), source='patient', write_only=True, required=False
    )
    cancer_type_id = serializers.PrimaryKeyRelatedField(
        queryset=CancerType.objects.all(), source='cancer_type', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = CancerCase
        fields = [
            'id_cancer', 'patient', 'patient_id', 'cancer_type', 'cancer_type_id', 'cancer_type_detail',
            'taille_cancer', 'type_cancer', 'sous_type', 'niveau', 'etat', 'date_diagnostic',
            'dynamic_attributes',
            'anapath', 'imagings', 'analyses', 'treatments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id_cancer', 'created_at', 'updated_at']

    @transaction.atomic
    def create(self, validated_data):
        anapath_data = validated_data.pop('anapath', None)
        imagings_data = validated_data.pop('imagings', [])
        analyses_data = validated_data.pop('analyses', [])
        treatments_data = validated_data.pop('treatments', [])
        
        cancer_case = CancerCase.objects.create(**validated_data)
        
        if anapath_data:
            Anapath.objects.create(cancer_case=cancer_case, **anapath_data)
            
        for imaging_data in imagings_data:
            Imaging.objects.create(cancer_case=cancer_case, **imaging_data)
            
        for analysis_data in analyses_data:
            Analysis.objects.create(cancer_case=cancer_case, **analysis_data)
            
        for treatment_data in treatments_data:
            CancerTreatment.objects.create(cancer_case=cancer_case, **treatment_data)
            
        return cancer_case

    @transaction.atomic
    def update(self, instance, validated_data):
        # Handle basic fields
        anapath_data = validated_data.pop('anapath', None)
        imagings_data = validated_data.pop('imagings', None)
        analyses_data = validated_data.pop('analyses', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update Anapath
        if anapath_data:
            anapath_obj, created = Anapath.objects.get_or_create(cancer_case=instance)
            for attr, value in anapath_data.items():
                setattr(anapath_obj, attr, value)
            anapath_obj.save()
            
        # For simplicity in this demo, imagings and analyses are just appended if passed
        # In a real app, you might want more complex sync logic
        if imagings_data:
            # Optional: clear existing if you want full overwrite
            # instance.imagings.all().delete()
            for imaging_data in imagings_data:
                Imaging.objects.create(cancer_case=instance, **imaging_data)
                
        if analyses_data:
            for analysis_data in analyses_data:
                Analysis.objects.create(cancer_case=instance, **analysis_data)
                
        return instance

        return instance
