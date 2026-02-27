from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Utilisateur, MedecinProfile, AdminSystemeProfile

class UtilisateurTests(TestCase):
    def test_create_user(self):
        user = Utilisateur.objects.create_user(
            email="test@test.com",
            password="testpassword123",
            nom="TestNom",
            prenom="TestPrenom",
            n_carte_nationale="123456789",
            sexe="M",
            role=Utilisateur.Role.MEDECIN
        )
        self.assertEqual(user.email, "test@test.com")
        self.assertTrue(user.is_active)
        # Vérifier le signal
        self.assertTrue(MedecinProfile.objects.filter(utilisateur=user).exists())
    def test_admin_is_staff_auto_assignment(self):
        admin_user = Utilisateur.objects.create_user(
            email="admin_staff@test.com",
            password="adminpassword123",
            nom="Admin",
            prenom="Staff",
            n_carte_nationale="STAFF123",
            sexe="M",
            role=Utilisateur.Role.ADMIN
        )
        self.assertFalse(admin_user.is_staff)
        self.assertFalse(admin_user.is_superuser)
        self.assertTrue(AdminSystemeProfile.objects.filter(utilisateur=admin_user).exists())

class RBACAPITests(APITestCase):
    def setUp(self):
        self.admin_user = Utilisateur.objects.create_user(
            email="admin@test.com",
            password="adminpassword123",
            nom="Admin",
            prenom="Test",
            n_carte_nationale="ADM123",
            sexe="M",
            role=Utilisateur.Role.ADMIN
        )
        self.medecin_user = Utilisateur.objects.create_user(
            email="medecin@test.com",
            password="medecinpassword123",
            nom="Medecin",
            prenom="Test",
            n_carte_nationale="MED123",
            sexe="F",
            role=Utilisateur.Role.MEDECIN
        )

    def test_admin_access_to_admin_endpoint(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('test_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_medecin_access_to_admin_endpoint_denied(self):
        self.client.force_authenticate(user=self.medecin_user)
        url = reverse('test_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_medecin_access_to_medecin_endpoint(self):
        self.client.force_authenticate(user=self.medecin_user)
        url = reverse('test_medecin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
