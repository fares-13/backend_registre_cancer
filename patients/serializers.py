from rest_framework import serializers
from .models import Patient, QuestionHabitude, ReponseHabitude, AntecedentFamilial, PatientOnboardingToken

class QuestionHabitudeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionHabitude
        fields = '__all__'

class ReponseHabitudeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReponseHabitude
        fields = '__all__'

class AntecedentFamilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentFamilial
        fields = '__all__'

class PatientOnboardingTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientOnboardingToken
        fields = ['token', 'expires_at', 'is_used', 'is_valid']

class PatientSerializer(serializers.ModelSerializer):
    onboarding_token = serializers.SerializerMethodField()
    habitudes_reponses = ReponseHabitudeSerializer(many=True, read_only=True)
    antecedents_familiaux = AntecedentFamilialSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = '__all__'

    def get_onboarding_token(self, obj):
        try:
            # Assumes one-to-one backward relation
            token_obj = obj.onboarding_token
            return PatientOnboardingTokenSerializer(token_obj).data
        except PatientOnboardingToken.DoesNotExist:
            return None
