from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, QuestionHabitudeViewSet, PublicOnboardingViewSet

router = DefaultRouter()
router.register(r'questions-habitudes', QuestionHabitudeViewSet, basename='question-habitude')
router.register(r'public-onboarding', PublicOnboardingViewSet, basename='public-onboarding')
router.register(r'', PatientViewSet, basename='patient')

urlpatterns = [
    path('', include(router.urls)),
]
