from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RcpSessionViewSet, RcpParticipantViewSet, RcpCaseViewSet,
    RcpDecisionViewSet, RcpProtocolViewSet, RcpTemplateViewSet, RcpMessageViewSet
)

router = DefaultRouter()
router.register(r'sessions', RcpSessionViewSet, basename='rcp-sessions')
router.register(r'participants', RcpParticipantViewSet, basename='rcp-participants')
router.register(r'cases', RcpCaseViewSet, basename='rcp-cases')
router.register(r'decisions', RcpDecisionViewSet, basename='rcp-decisions')
router.register(r'protocols', RcpProtocolViewSet, basename='rcp-protocols')
router.register(r'templates', RcpTemplateViewSet, basename='rcp-templates')
router.register(r'messages', RcpMessageViewSet, basename='rcp-messages')

urlpatterns = [
    path('', include(router.urls)),
]
