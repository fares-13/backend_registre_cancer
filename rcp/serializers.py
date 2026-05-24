from rest_framework import serializers
from .models import RcpSession, RcpParticipant, RcpCase, RcpDecision, RcpProtocol, RcpTemplate, RcpMessage, RcpNotification
from accounts.serializers import UtilisateurSerializer
from accounts.models import Utilisateur
from cancers.serializers import CancerCaseSerializer
from cancers.models import CancerCase
from patients.models import Patient

class RcpParticipantSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    specialty = serializers.SerializerMethodField()
    userId = serializers.IntegerField(source='user_id', read_only=True)

    class Meta:
        model = RcpParticipant
        fields = '__all__'
        extra_kwargs = {
            'user': {'write_only': True},
        }

    def get_name(self, obj):
        return obj.user.get_full_name()

    def get_specialty(self, obj):
        if hasattr(obj.user, 'profile_medecin') and obj.user.profile_medecin:
            return obj.user.profile_medecin.specialite
        return obj.user.role if obj.user.role else ''

class RcpParticipantCreateSerializer(serializers.ModelSerializer):
    userId = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = RcpParticipant
        fields = ['rcp', 'role', 'isRequired', 'userId']

    def validate_userId(self, value):
        if not Utilisateur.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found")
        return value

    def create(self, validated_data):
        user_id = validated_data.pop('userId')
        validated_data['user_id'] = user_id
        return super().create(validated_data)

class RcpSessionSerializer(serializers.ModelSerializer):
    coordinatorName = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    casesCount = serializers.IntegerField(read_only=True)
    participantsCount = serializers.IntegerField(read_only=True)
    id = serializers.CharField(max_length=50, required=False)

    class Meta:
        model = RcpSession
        fields = '__all__'

class RcpCaseSerializer(serializers.ModelSerializer):
    patientName = serializers.SerializerMethodField()
    patientAge = serializers.SerializerMethodField()
    cancerType = serializers.SerializerMethodField()
    subType = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()
    presenterName = serializers.SerializerMethodField()
    patientId = serializers.UUIDField(source='cancer_case.patient_id', read_only=True)
    caseId = serializers.UUIDField(source='cancer_case_id', read_only=True)

    class Meta:
        model = RcpCase
        fields = '__all__'

    def get_patientName(self, obj):
        return f"{obj.cancer_case.patient.nom} {obj.cancer_case.patient.prenom}"

    def get_patientAge(self, obj):
        return obj.cancer_case.patient.age_current or 0

    def get_cancerType(self, obj):
        if obj.cancer_case.cancer_type:
            return obj.cancer_case.cancer_type.nom
        return obj.cancer_case.type_cancer or ''

    def get_subType(self, obj):
        return obj.cancer_case.sous_type or ''

    def get_stage(self, obj):
        return obj.cancer_case.niveau or ''

    def get_presenterName(self, obj):
        if obj.presenter:
            return obj.presenter.get_full_name()
        return ''

class RcpCaseCreateSerializer(serializers.ModelSerializer):
    cancerCaseId = serializers.UUIDField(write_only=True, required=True)
    presenterId = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = RcpCase
        fields = ['rcp', 'cancerCaseId', 'presenterId', 'order', 'notes']

    def validate_cancerCaseId(self, value):
        if not CancerCase.objects.filter(id_cancer=value).exists():
            raise serializers.ValidationError("Cancer case not found")
        return value

    def create(self, validated_data):
        cancer_case_id = validated_data.pop('cancerCaseId')
        presenter_id = validated_data.pop('presenterId', None)
        validated_data['cancer_case_id'] = cancer_case_id
        if presenter_id:
            validated_data['presenter_id'] = presenter_id
        return super().create(validated_data)

class RcpDecisionSerializer(serializers.ModelSerializer):
    patientName = serializers.SerializerMethodField()
    validatedByName = serializers.CharField(source='validatedBy.get_full_name', read_only=True)

    def get_patientName(self, obj):
        return f"{obj.rcp_case.cancer_case.patient.nom} {obj.rcp_case.cancer_case.patient.prenom}"

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
    senderSpecialty = serializers.SerializerMethodField()
    senderId = serializers.IntegerField(source='sender_id', read_only=True)

    class Meta:
        model = RcpMessage
        fields = '__all__'
        read_only_fields = ['sender', 'readBy']

    def get_senderSpecialty(self, obj):
        if hasattr(obj.sender, 'profile_medecin') and obj.sender.profile_medecin:
            return obj.sender.profile_medecin.specialite
        return obj.sender.role if obj.sender.role else ''

class RcpMessageCreateSerializer(serializers.ModelSerializer):
    rcpCaseId = serializers.UUIDField(source='rcp_case_id', write_only=True, required=False, allow_null=True)

    class Meta:
        model = RcpMessage
        fields = ['rcp', 'rcpCaseId', 'content', 'type', 'attachments']

class RcpNotificationSerializer(serializers.ModelSerializer):
    rcpTitle = serializers.CharField(source='rcp.title', read_only=True)

    class Meta:
        model = RcpNotification
        fields = '__all__'
