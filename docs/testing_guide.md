# Guide: Apprendre à tester avec `tests.py`

Le fichier `tests.py` dans Django est l'endroit où vous écrivez des tests automatisés pour vérifier que votre code fonctionne comme prévu.

## Pourquoi tester ?
- **Confiance** : Soyez sûr que vos changements ne cassent rien.
- **Documentation** : Les tests montrent comment votre code est censé être utilisé.
- **Vitesse** : Plus besoin de tester manuellement chaque clic dans le navigateur.

## Types de tests dans ce projet

### 1. Tests de Modèles (`TestCase`)
Ils vérifient que vos modèles se comportent correctement (ex: création d'un utilisateur, signaux).

```python
from django.test import TestCase
from .models import Utilisateur

class MyModelTest(TestCase):
    def test_user_creation(self):
        user = Utilisateur.objects.create_user(email="test@example.com", password="password123", ...)
        self.assertEqual(user.email, "test@example.com")
```

### 2. Tests d'API (`APITestCase`)
Ils simulent des requêtes HTTP (GET, POST, etc.) vers vos endpoints pour vérifier les réponses et les permissions.

```python
from rest_framework.test import APITestCase
from django.urls import reverse

class MyApiTest(APITestCase):
    def test_get_profile(self):
        self.client.force_authenticate(user=my_user) # Simule une connexion
        response = self.client.get(reverse('profile-detail'))
        self.assertEqual(response.status_code, 200)
```

## Comment lancer les tests ?
Ouvrez votre terminal dans le dossier du projet et tapez :
```bash
python manage.py test accounts
```

## Analyse de vos tests actuels
Dans votre fichier `accounts/tests.py` :
- `test_create_user` : Vérifie que le signal crée bien un profil quand un utilisateur est créé.
- `test_admin_access_to_admin_endpoint` : Vérifie que seul un ADMIN peut accéder à la vue protégée.

> [!TIP]
> Toujours lancer les tests après chaque modification importante !
