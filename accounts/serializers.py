from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Utilisateur

class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ('id', 'nom', 'prenom', 'email', 'telephone', 'n_carte_nationale', 'sexe', 'role', 'date_creation', 'is_active', 'last_login')
        read_only_fields = ('id', 'date_creation', 'last_login')

    def validate_role(self, value):
        if value == Utilisateur.Role.ADMIN:
            raise serializers.ValidationError("La création ou modification d'un compte Administrateur n'est pas autorisée via cette interface.")
        return value

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = Utilisateur
        fields = ('nom', 'prenom', 'email', 'telephone', 'n_carte_nationale', 'sexe', 'role', 'password')

    def validate_role(self, value):
        if value == Utilisateur.Role.ADMIN:
            raise serializers.ValidationError("La création d'un compte Administrateur n'est pas autorisée via cette interface.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['nom'] = user.nom
        token['prenom'] = user.prenom
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        return data

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not Utilisateur.objects.filter(email=value).exists():
            # Pour la sécurité (prévention de l'énumération), 
            # on pourrait ne pas lever d'erreur ici, 
            # mais le service gérera l'envoi silencieux.
            pass
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
            
        return attrs
