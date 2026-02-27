# Architecture: Système d'Authentification Frontend (React + Django JWT)

Ce document détaille l'implémentation de l'authentification et de l'autorisation au niveau du Frontend pour le projet **Registre Cancer**.

## 1. Flux JWT (JSON Web Token)

Le système repose sur une stratégie de tokens doubles : **Access Token** (courte durée) et **Refresh Token** (longue durée).

### Acquisition des Tokens
1. Le Frontend envoie les identifiants (`email`, `password`) à `/api/accounts/login/`.
2. Le Backend valide et renvoie deux tokens dans le corps de la réponse JSON :
   ```json
   {
     "access": "eyJhbG...",
     "refresh": "eyJhbG...",
     "role": "MEDECIN"
   }
   ```

### Stockage des Tokens : Comparatif Stratégique

| Méthode | Sécurité | Persistance | Risque principal |
| :--- | :--- | :--- | :--- |
| **localStorage** | Faible | Élevée (survit au refresh) | Vol via XSS (Cross-Site Scripting) |
| **sessionStorage** | Moyenne | Basse (onglet fermé = logout) | XSS |
| **In-Memory (JS State)** | Élevée | Nulle (logout au refresh F5) | Perte de session fluide |
| **httpOnly Cookies** | Maximale | Élevée | CSRF (Cross-Site Request Forgery) |

**Recommandation Senior :**
Pour une application de santé sensible, l'idéal est de stocker le **Access Token en mémoire (React State)** et le **Refresh Token dans un cookie `httpOnly` + `Secure`**. Si pour des raisons de simplicité de développement vous utilisez `localStorage`, assurez-vous d'avoir une politique de sécurité de contenu (CSP) stricte contre le XSS.

### Envoi des headers
Chaque requête vers une API protégée doit inclure :
`Authorization: Bearer <access_token>`

### Rafraîchissement Automatique (Silent Refresh)
Utiliser un **intercepteur Axios**. Si une requête échoue avec une erreur `401 Unauthorized`, l'intercepteur :
1. "Met en pause" les requêtes sortantes.
2. Appelle l'endpoint de rafraîchissement avec le `refresh_token`.
3. Met à jour le `access_token` en mémoire.
4. Relance la requête initiale avec le nouveau token.

---

## 2. Gestion des Rôles (RBAC)

### Identification du rôle
Le Frontend ne doit pas faire confiance aveugle au corps de la réponse. Le rôle doit être extrait directement du payload du JWT (décodage Base64 de la partie centrale du token) pour garantir son intégrité.

### Route Guards (Protections de routes)
Implémenter un composant `ProtectedRoute` de haut niveau :
```jsx
const ProtectedRoute = ({ allowedRoles, children }) => {
  const { user, isAuthenticated } = useAuth();
  
  if (!isAuthenticated) return <Navigate to="/login" />;
  if (!allowedRoles.includes(user.role)) return <Navigate to="/unauthorized" />;
  
  return children;
};
```

### UI Conditionnelle
Utiliser une fonction utilitaire `hasPermission(role)` pour masquer les éléments de navigation ou les boutons d'action (ex: bouton "Supprimer" visible uniquement pour `ADMIN`).

---

## 3. Intégration et État Global

### Gestion de l'état
Utiliser **React Context API** ou **Zustand** (plus léger et performant) pour stocker :
- `user`: `{ email, nom, role, ... }`
- `isAuthenticated`: `boolean`
- `isLoading`: `boolean` (pendant la vérification initiale du token)

### Architecture des services
Créer une instance Axios dédiée avec une base URL prédéfinie et les intercepteurs configurés.
- `authService.js` : Login, Logout, Refresh.
- `apiClient.js` : Requêtes business sécurisées.

---

## 4. Gestion des Erreurs et Sécurité

### Cycle de vie des erreurs
- **401 (Expired/Invalid)** : Tentative de rafraîchissement. Si échec -> Clear Global State -> Redirect Login.
- **403 (Forbidden)** : Redirection vers une page "Accès Refusé" (l'utilisateur est logué mais n'a pas les droits).

### Sécurité (XSS & CSRF)
- **Nettoyage des entrées** : React protège par défaut contre le XSS simple, mais attention aux `dangerouslySetInnerHTML`.
- **CSRF Token** : Si utilisation de cookies pour la session, inclure le header `X-CSRFToken` fourni par Django.

---

## 5. Diagramme de Séquence (JWT Flow)

1. **Login** -> Envoi Email/Pass -> Réception Access + Refresh.
2. **Requête API** -> Envoi Access Token en Header.
3. **Expiration** -> 401 reçu -> Refresh auto avec Refresh Token.
4. **Logout** -> Suppression des tokens (State + Storage) -> Redirection Login.

---

## 6. Outils recommandés

1. **Axios** : Pour la gestion simplifiée des intercepteurs.
2. **React Query (TanStack Query)** : Pour synchroniser l'état serveur et UI.
3. **Zustand** : Pour un état global léger.
4. **jwt-decode** : Pour lire les infos du token côté client.
