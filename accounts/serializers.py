from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Utilisateur

class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ('id', 'nom', 'prenom', 'email', 'telephone', 'n_carte_nationale', 'sexe', 'role', 'date_creation')
        read_only_fields = ('id', 'date_creation')

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Ajouter le rôle au payload du JWT
        token['role'] = user.role
        token['nom'] = user.nom
        token['prenom'] = user.prenom
        
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Ajouter le rôle à la réponse JSON du login (optionnel mais utile)
        data['role'] = self.user.role
        return data
