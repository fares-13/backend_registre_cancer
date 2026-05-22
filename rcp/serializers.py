from rest_framework import serializers
from .models import RcpSession, RcpParticipant, RcpCase, RcpDecision, RcpProtocol, RcpTemplate, RcpMessage
from accounts.serializers import UtilisateurSerializer
from cancers.serializers import CancerCaseSerializer

class RcpParticipantSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    specialty = serializers.CharField(source='user.specialite', read_only=True)
    
    class Meta:
        model = RcpParticipant
        fields = '__all__'

class RcpSessionSerializer(serializers.ModelSerializer):
    coordinatorName = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    casesCount = serializers.IntegerField(read_only=True)
    participantsCount = serializers.IntegerField(read_only=True)
    id = serializers.CharField(max_length=50, required=False)

    class Meta:
        model = RcpSession
        fields = '__all__'

class RcpCaseSerializer(serializers.ModelSerializer):
    patientName = serializers.CharField(source='cancer_case.patient.nom', read_only=True)
    patientAge = serializers.IntegerField(source='cancer_case.patient.age_current', read_only=True, default=0) # Need property on patient if it exists
    cancerType = serializers.CharField(source='cancer_case.type_cancer.nom', read_only=True)
    subType = serializers.CharField(source='cancer_case.sous_type.nom', read_only=True, default='')
    stage = serializers.CharField(source='cancer_case.stade', read_only=True, default='')
    presenterName = serializers.CharField(source='presenter.get_full_name', read_only=True)

    class Meta:
        model = RcpCase
        fields = '__all__'

class RcpDecisionSerializer(serializers.ModelSerializer):
    patientName = serializers.CharField(source='rcp_case.cancer_case.patient.nom', read_only=True)
    validatedByName = serializers.CharField(source='validatedBy.get_full_name', read_only=True)

    class Meta:
        model = RcpDecision
        fields = '__all__'

class RcpProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = RcpProtocol
        fields = '__all__'

class RcpTemplateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(max_length=50, required=False)
    class Meta:
        model = RcpTemplate
        fields = '__all__'

class RcpMessageSerializer(serializers.ModelSerializer):
    senderName = serializers.CharField(source='sender.get_full_name', read_only=True)
    senderSpecialty = serializers.CharField(source='sender.specialite', read_only=True)

    class Meta:
        model = RcpMessage
        fields = '__all__'
        read_only_fields = ['sender', 'readBy']

