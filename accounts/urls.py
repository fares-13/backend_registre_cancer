from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, 
    LogoutView, 
    AdminOnlyView, 
    ArchitectOnlyView, 
    MedecinOnlyView, 
    EpidemiologisteOnlyView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Auth endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # User management
    path('', include(router.urls)),
    
    # RBAC Test endpoints
    path('test-admin/', AdminOnlyView.as_view(), name='test_admin'),
    path('test-architect/', ArchitectOnlyView.as_view(), name='test_architect'),
    path('test-medecin/', MedecinOnlyView.as_view(), name='test_medecin'),
    path('test-epidemio/', EpidemiologisteOnlyView.as_view(), name='test_epidemio'),
]
