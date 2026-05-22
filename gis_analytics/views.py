import logging
from datetime import datetime

from django.db.models import Q
from rest_framework import viewsets, views, status, permissions
from rest_framework.response import Response

from .models import Zone, ZoneDataSource, AreaLayer
from .serializers import ZoneSerializer, ZoneListSerializer, ZoneDataSourceSerializer, AreaLayerSerializer
from .services import point_in_zone, SHAPELY_AVAILABLE

from cancers.models import CancerCase

logger = logging.getLogger(__name__)

# Safety limit: maximum cancer cases loaded into Python memory per request.
# For very large datasets, this should be moved to a background task (Celery).
MAX_CASES_IN_MEMORY = 10_000


class ZoneViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for geographic zones.
    GET /api/gis/zones/         - List all zones (lightweight)
    GET /api/gis/zones/{id}/    - Zone detail with geojson + data sources
    POST /api/gis/zones/        - Create zone (auto-assigns created_by)
    PATCH /api/gis/zones/{id}/  - Update zone
    DELETE /api/gis/zones/{id}/ - Delete zone
    """
    queryset = Zone.objects.all().prefetch_related('data_sources').order_by('-created_at')
    serializer_class = ZoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ZoneListSerializer
        return ZoneSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class GisAnalyzeView(views.APIView):
    """
    POST /api/gis/analyze/

    Analyze the distribution of cancer cases across geographic zones.

    Strategy (optimized for large datasets):
    1. Filter CancerCase using indexed DB columns FIRST (SQL-side, fast).
    2. Only load patients that have coordinates.
    3. Python-side point-in-polygon per zone using shapely (bounded result set).
    4. Aggregate stats per zone and return.

    Request body:
    {
        "zones": ["zone-uuid-1", "zone-uuid-2"],       // Empty = all zones
        "cancer_filters": {
            "type": "lung",                             // Optional: legacy string search
            "cancer_types": ["uuid1", "uuid2"],         // Optional: dynamic list from dropdown
            "sexe": "M",                                // Optional: M|F
            "date_range": ["2020-01-01", "2025-01-01"] // Optional
        },
        "chart_type": "bar"                             // map|bar|line|pie
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not SHAPELY_AVAILABLE:
            return Response(
                {'error': 'La bibliothèque shapely est requise. Exécutez: pip install shapely'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        zone_ids     = request.data.get('zones', [])
        cancer_filters = request.data.get('cancer_filters', {})
        chart_type   = request.data.get('chart_type', 'bar')

        # ── 1. Fetch zones or area_layers ───────────────────────────────────
        zone_ids = request.data.get('zones', [])
        area_layer_ids = request.data.get('area_layers', [])
        
        zones = []
        area_layers = []
        if zone_ids:
            zones = list(Zone.objects.filter(id__in=zone_ids).prefetch_related('data_sources'))
        elif area_layer_ids:
            from .models import AreaLayer
            area_layers = list(AreaLayer.objects.filter(id__in=area_layer_ids))
        else:
            zones = list(Zone.objects.all().prefetch_related('data_sources'))

        if not zones and not area_layers:
            return Response({'error': 'Aucune zone ou couche spatiale trouvée.'}, status=status.HTTP_404_NOT_FOUND)

        # ── 2. Filter cancer cases with indexed queries (DB-side) ──────────
        cases_qs = CancerCase.objects.select_related('patient', 'cancer_type')

        cancer_type_filter = (cancer_filters.get('type') or '').strip()
        cancer_type_ids    = cancer_filters.get('cancer_types', [])
        sexe_filter        = (cancer_filters.get('sexe') or '').strip()
        date_range         = cancer_filters.get('date_range', [])

        # Filter by specific UUIDs from dropdown (new logic)
        if cancer_type_ids:
            if isinstance(cancer_type_ids, str):
                cancer_type_ids = [cancer_type_ids]
            cases_qs = cases_qs.filter(cancer_type_id__in=cancer_type_ids)
        # Filter by string search (legacy logic)
        elif cancer_type_filter:
            cases_qs = cases_qs.filter(
                Q(type_cancer__icontains=cancer_type_filter) |
                Q(cancer_type__nom__icontains=cancer_type_filter)
            )

        if sexe_filter in ('M', 'F'):
            cases_qs = cases_qs.filter(patient__sexe=sexe_filter)

        if len(date_range) == 2:
            try:
                d_start = datetime.strptime(date_range[0], '%Y-%m-%d').date()
                d_end   = datetime.strptime(date_range[1], '%Y-%m-%d').date()
                cases_qs = cases_qs.filter(created_at__date__range=(d_start, d_end))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid date_range in GIS analyze: {e}")

        # Only patients with coordinates can be assigned to a zone
        cases_qs = cases_qs.filter(
            patient__latitude__isnull=False,
            patient__longitude__isnull=False,
        )

        # Project only the columns we need (reduces memory)
        cases_data = list(cases_qs.values(
            'id_cancer',
            'patient__id_malade',
            'patient__latitude',
            'patient__longitude',
            'patient__deces',
            'patient__sexe',
            'patient__date_naissance',
            'patient__adresse',
            'type_cancer',
            'cancer_type__nom',
            'etat',
            'created_at',
        )[:MAX_CASES_IN_MEMORY])

        total_cases = len(cases_data)

        # ── 3. Spatial grouping per zone/layer ─────────────────────────────
        results = []
        
        def compute_metrics(zone_cases):
            count     = len(zone_cases)
            deceased  = sum(1 for c in zone_cases if c.get('patient__deces'))
            mortality_rate = round(deceased / count * 100, 2) if count > 0 else 0.0

            # Gender distribution
            male   = sum(1 for c in zone_cases if c.get('patient__sexe') == 'M')
            female = count - male

            # Cancer type distribution
            type_dist: dict[str, int] = {}
            for c in zone_cases:
                t = c.get('cancer_type__nom') or c.get('type_cancer') or 'Inconnu'
                type_dist[t] = type_dist.get(t, 0) + 1
                
            # Age distribution
            age_dist = {'0-18': 0, '19-35': 0, '36-50': 0, '51-65': 0, '65+': 0}
            today = datetime.now().date()
            for c in zone_cases:
                dob = c.get('patient__date_naissance')
                if dob:
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    if age <= 18: age_dist['0-18'] += 1
                    elif age <= 35: age_dist['19-35'] += 1
                    elif age <= 50: age_dist['36-50'] += 1
                    elif age <= 65: age_dist['51-65'] += 1
                    else: age_dist['65+'] += 1
            
            # Temporal trend (by year/month)
            trend_dist: dict[str, int] = {}
            for c in zone_cases:
                cat = c.get('created_at')
                if cat:
                    month_key = cat.strftime('%Y-%m')
                    trend_dist[month_key] = trend_dist.get(month_key, 0) + 1

            return {
                'count': count,
                'deceased': deceased,
                'mortality_rate': mortality_rate,
                'male': male,
                'female': female,
                'type_dist': type_dist,
                'age_dist': age_dist,
                'trend_dist': trend_dist
            }

        if zones:
            for zone in zones:
                zone_cases = [
                    c for c in cases_data
                    if point_in_zone(c['patient__latitude'], c['patient__longitude'], zone.geojson)
                ]
                metrics = compute_metrics(zone_cases)
                
                # Enrich with environmental data
                latest_source = max(zone.data_sources.all(), key=lambda ds: ds.year, default=None)
                incidence_rate = None
                if latest_source and latest_source.population and latest_source.population > 0:
                    incidence_rate = round(metrics['count'] / latest_source.population * 100_000, 2)

                results.append({
                    'zone_id':    str(zone.id),
                    'zone_name':  zone.name,
                    'zone_type':  zone.type,
                    'pollution_level': latest_source.pollution_level if latest_source else None,
                    'population':      latest_source.population      if latest_source else None,
                    'incidence':       metrics['count'],
                    'incidence_rate':  incidence_rate,
                    'mortality_rate':  metrics['mortality_rate'],
                    'deceased_count':  metrics['deceased'],
                    'gender_distribution':      {'M': metrics['male'], 'F': metrics['female']},
                    'cancer_type_distribution': metrics['type_dist'],
                    'age_distribution':         metrics['age_dist'],
                    'temporal_trend':           metrics['trend_dist'],
                    'geojson': zone.geojson,
                })
        elif area_layers:
            for layer in area_layers:
                layer_regions = layer.regions if isinstance(layer.regions, list) else []
                # Fallback matching by address containing region name
                zone_cases = [
                    c for c in cases_data
                    if any(r.lower() in (c.get('patient__adresse') or '').lower() for r in layer_regions)
                ]
                metrics = compute_metrics(zone_cases)
                
                results.append({
                    'zone_id':    str(layer.id),
                    'zone_name':  layer.title,
                    'zone_type':  'AreaLayer',
                    'pollution_level': None,
                    'population':      None,
                    'incidence':       metrics['count'],
                    'incidence_rate':  None,
                    'mortality_rate':  metrics['mortality_rate'],
                    'deceased_count':  metrics['deceased'],
                    'gender_distribution':      {'M': metrics['male'], 'F': metrics['female']},
                    'cancer_type_distribution': metrics['type_dist'],
                    'age_distribution':         metrics['age_dist'],
                    'temporal_trend':           metrics['trend_dist'],
                    'color': layer.color,
                })

        # Sort by incidence descending for easier consumption by charts
        results.sort(key=lambda z: z['incidence'], reverse=True)

        return Response({
            'chart_type':          chart_type,
            'total_filtered_cases': total_cases,
            'zones':               results,
        }, status=status.HTTP_200_OK)


class AreaLayerViewSet(viewsets.ModelViewSet):
    """
    CRUD for AreaLayers.
    Architect role uses this to define new colored area layers.
    """
    queryset = AreaLayer.objects.all().order_by('-created_at')
    serializer_class = AreaLayerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class GisCompareView(views.APIView):
    """
    GET /api/gis/compare/

    Compare a manually defined AreaLayer with cancer distribution.

    Query parameters:
    - area_layer_id: UUID of the AreaLayer
    - cancer_type_id: UUID of the CancerType to filter by (optional, empty means all)

    Returns:
    - area_layer: details of the layer (color, regions)
    - cancer_distribution: count of cases per region
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        area_layer_id = request.query_params.get('area_layer_id')
        cancer_type_id = request.query_params.get('cancer_type_id')

        if not area_layer_id:
            return Response({'error': 'area_layer_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            area_layer = AreaLayer.objects.get(id=area_layer_id)
        except AreaLayer.DoesNotExist:
            return Response({'error': 'AreaLayer not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Base queryset
        cases_qs = CancerCase.objects.select_related('patient')

        # Filter by cancer type if provided
        if cancer_type_id:
            cases_qs = cases_qs.filter(cancer_type_id=cancer_type_id)

        cancer_distribution = []
        regions = area_layer.regions if isinstance(area_layer.regions, list) else []

        for region_name in regions:
            # We match cases where the patient's address contains the region name
            count = cases_qs.filter(patient__adresse__icontains=region_name).count()
            cancer_distribution.append({
                'region': region_name,
                'count': count
            })

        # Get the actual points for the cases
        # Filter to only cases with coordinates
        points_qs = cases_qs.filter(
            patient__latitude__isnull=False,
            patient__longitude__isnull=False
        )

        # We DO NOT filter by region_queries here because the Epidemiologist
        # wants to visually compare ALL points of the selected cancer type
        # against the area polygon.

        points_data = points_qs.values(
            'patient__latitude',
            'patient__longitude',
            'cancer_type__nom',
            'patient__sexe'
        )

        points = [
            {
                'lat': p['patient__latitude'],
                'lng': p['patient__longitude'],
                'type': p['cancer_type__nom'],
                'sexe': p['patient__sexe']
            } for p in points_data
        ]

        return Response({
            'area_layer': AreaLayerSerializer(area_layer).data,
            'cancer_distribution': cancer_distribution,
            'points': points,
        }, status=status.HTTP_200_OK)

