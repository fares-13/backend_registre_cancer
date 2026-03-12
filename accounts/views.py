from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import CustomTokenObtainPairSerializer, UtilisateurSerializer
from .permissions import IsAdmin, IsArchitect, IsMedecin, IsEpidemiologiste

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    # In this new version we allow the refresh token to be passed in the body natively.
    pass

class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

# Endpoints de test pour vérifier le RBAC

class AdminOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    def get(self, request):
        return Response({"message": "Bienvenue, Administrateur!"})

class ArchitectOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsArchitect]
    def get(self, request):
        return Response({"message": "Bienvenue, Architecte!"})

class MedecinOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsMedecin]
    def get(self, request):
        return Response({"message": "Bienvenue, Docteur!"})

class EpidemiologisteOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsEpidemiologiste]
    def get(self, request):
        return Response({"message": "Bienvenue, Epidémiologiste!"})
