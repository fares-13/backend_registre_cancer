from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ZoneViewSet, GisAnalyzeView, AreaLayerViewSet, GisCompareView, CommuneViewSet

router = DefaultRouter()
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'area-layers', AreaLayerViewSet, basename='arealayer')
router.register(r'communes', CommuneViewSet, basename='commune')

urlpatterns = [
    path('', include(router.urls)),
    path('analyze/', GisAnalyzeView.as_view(), name='gis-analyze'),
    path('compare/', GisCompareView.as_view(), name='gis-compare'),
]
