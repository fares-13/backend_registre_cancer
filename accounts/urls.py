from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, 
    LogoutView, 
    AdminOnlyView, 
    ArchitectOnlyView, 
    MedecinOnlyView, 
    EpidemiologisteOnlyView
)

urlpatterns = [
    # Auth endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    
    # Test RBAC endpoints
    path('test-admin/', AdminOnlyView.as_view(), name='test_admin'),
    path('test-architect/', ArchitectOnlyView.as_view(), name='test_architect'),
    path('test-medecin/', MedecinOnlyView.as_view(), name='test_medecin'),
    path('test-epidemiologiste/', EpidemiologisteOnlyView.as_view(), name='test_epidemiologiste'),
]
