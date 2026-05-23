from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CancerCaseViewSet, AnapathViewSet, 
    ImagingViewSet, AnalysisViewSet,
    CancerTypeViewSet, CancerAttributeViewSet,
    CancerTreatmentViewSet, ImagingTypeViewSet, AnalysisTypeViewSet,
    MolecularMarkerViewSet, FollowUpViewSet
)
from .statistics_views import StatisticsViewSet

router = DefaultRouter()
router.register(r'types', CancerTypeViewSet, basename='cancer-type')
router.register(r'attributes', CancerAttributeViewSet, basename='cancer-attribute')
router.register(r'imaging-types', ImagingTypeViewSet, basename='imaging-type')
router.register(r'analysis-types', AnalysisTypeViewSet, basename='analysis-type')
router.register(r'cases', CancerCaseViewSet, basename='cancer-case')
router.register(r'anapath', AnapathViewSet, basename='anapath')
router.register(r'imaging', ImagingViewSet, basename='imaging')
router.register(r'analyses', AnalysisViewSet, basename='analysis')
router.register(r'treatments', CancerTreatmentViewSet, basename='treatment')
router.register(r'molecular-markers', MolecularMarkerViewSet, basename='molecular-marker')
router.register(r'followups', FollowUpViewSet, basename='followup')
router.register(r'statistics', StatisticsViewSet, basename='statistics')

urlpatterns = [
    path('', include(router.urls)),
]
