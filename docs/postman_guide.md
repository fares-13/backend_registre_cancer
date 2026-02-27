## Prérequis pour la connexion

Pour qu'un utilisateur puisse se connecter à la plateforme (Frontend) :
1.  **`is_active`** : Doit être **`True`**. Si un compte est désactivé, le login échouera.
2.  **`is_staff`** : N'est **pas nécessaire** pour la plateforme. Cet attribut est réservé à l'accès à l'interface d'administration Django (`/admin`).

> [!NOTE]
> Un utilisateur avec le rôle `MEDECIN` ou `ADMIN` (plateforme) peut se connecter tant qu'il est "actif", même s'il n'est pas "staff".

Postman est un outil puissant pour tester vos API manuellement avant de les intégrer au Frontend.

## Étapes pour tester l'authentification JWT

### 1. Obtenir un Token (Login)
- **Méthode** : `POST`
- **URL** : `http://127.0.0.1:8000/api/accounts/login/`
- **Body** (JSON) :
  ```json
  {
      "email": "votre@email.com",
      "password": "votrepassword"
  }
  ```
- **Résultat** : Vous recevrez un `access` token et un `refresh` token.

### 2. Utiliser le Token pour les requêtes protégées
Pour chaque requête vers un endpoint protégé (ex: `/api/accounts/test-admin/`) :
1. Allez dans l'onglet **Authorization**.
2. Sélectionnez **Bearer Token** dans le menu Type.
3. Collez votre `access` token dans le champ Token.

### 3. Tester les différents rôles
- Créez des utilisateurs avec différents rôles (MEDECIN, ADMIN) via l'interface Admin Django (`/admin`).
- Essayez d'accéder aux endpoints avec leurs tokens respectifs pour vérifier que `permissions.py` fonctionne.

## Endpoints disponibles pour vos tests :
- `POST /api/accounts/login/` : Login
- `POST /api/accounts/logout/` : Logout (nécessite le `refresh` token dans le body)
- `GET /api/accounts/test-admin/` : Accessible uniquement par ADMIN
- `GET /api/accounts/test-medecin/` : Accessible uniquement par MEDECIN

> [!IMPORTANT]
> N'oubliez pas que le token 'access' expire rapidement. Si vous obtenez une erreur 401, vous devez vous reconnecter ou utiliser le 'refresh' token.
