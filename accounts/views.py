from rest_framework import status, generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Utilisateur
from .serializers import (
    CustomTokenObtainPairSerializer, 
    UtilisateurSerializer,
    UserCreateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)
from .permissions import IsAdmin, IsArchitect, IsMedecin, IsEpidemiologiste

# ... (Previous views remain unchanged)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
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

class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        try:
            user = Utilisateur.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Dans un environnement réel, l'URL de base viendrait des settings
            reset_url = f"http://localhost:5173/reset-password/{uid}/{token}/"
            
            subject = "Réinitialisation de votre mot de passe - Registre des Cancers"
            message = f"""
Bonjour {user.prenom} {user.nom},

Vous avez demandé la réinitialisation de votre mot de passe pour le Registre des Cancers.
Veuillez cliquer sur le lien ci-dessous pour définir un nouveau mot de passe :

{reset_url}

Ce lien expirera dans 30 minutes.

Si vous n'avez pas demandé cette réinitialisation, veuillez ignorer cet email.

Cordialement,
L'équipe du Registre des Cancers
Healthy Hospital – Tlemcen
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
        except Utilisateur.DoesNotExist:
            # Sécurité : ne pas révéler que l'email n'existe pas
            pass
            
        return Response(
            {"detail": "Si un compte est associé à cet email, un lien de réinitialisation a été envoyé."},
            status=status.HTTP_200_OK
        )

class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        
        if not uidb64 or not token:
            return Response({"error": "Paramètres manquants."}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = Utilisateur.objects.get(pk=id)
        except (TypeError, ValueError, OverflowError, Utilisateur.DoesNotExist):
            user = None
            
        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response({"detail": "Mot de passe réinitialisé avec succès."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Lien invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST)

from rest_framework import status, generics, viewsets, filters
# ... other imports ...

# --- User Management (Admin Only) ---
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'prenom', 'email', 'n_carte_nationale']
    ordering_fields = ['nom', 'date_creation', 'last_login']
    ordering = ['-date_creation']

    def get_queryset(self):
        # Strictly exclude ADMIN and superusers from the metier management API
        return Utilisateur.objects.exclude(
            role=Utilisateur.Role.ADMIN
        ).exclude(
            is_superuser=True
        ).order_by('-date_creation')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UtilisateurSerializer

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password_admin(self, request, pk=None):
        """Admin triggers a password reset email for a user."""
        user = self.get_object()
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        reset_url = f"http://localhost:5173/reset-password/{uid}/{token}/"
        
        subject = "Réinitialisation de mot de passe par l'administrateur"
        message = f"L'administrateur a demandé la réinitialisation de votre mot de passe.\n\nLien : {reset_url}"
        
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        return Response({"detail": f"Email de réinitialisation envoyé à {user.email}."}, status=status.HTTP_200_OK)

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
