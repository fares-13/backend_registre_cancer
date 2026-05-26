import io
import json
from datetime import datetime
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response

from .services import PDFReportGenerator
from gis_analytics.views import GisAnalyzeView
from cancers.statistics_views import StatisticsViewSet


def _make_internal_request(request, factory_method, view_class, data, suffix=''):
    """Helper to invoke an internal DRF view and return its response data."""
    from django.test import RequestFactory
    factory = RequestFactory()
    django_request = factory_method(data)
    if 'HTTP_AUTHORIZATION' in request.META:
        django_request.META['HTTP_AUTHORIZATION'] = request.META['HTTP_AUTHORIZATION']
    elif hasattr(request, '_request') and 'HTTP_AUTHORIZATION' in request._request.META:
        django_request.META['HTTP_AUTHORIZATION'] = request._request.META['HTTP_AUTHORIZATION']
    django_request.user = request.user
    view = view_class.as_view()
    response = view(django_request)
    if response.status_code != 200:
        return None
    return response.data


class ReportGenerateView(APIView):
    """
    POST /api/reports/generate/

    Generates a comprehensive PDF report with KPIs, charts, tables,
    geographic analysis, and data quality metrics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _normalize_filters(self, raw_filters):
        """Convert frontend nested filter format to flat StatisticsViewSet params."""
        params = {}
        cancer_filters = raw_filters.get('cancer_filters', {})
        date_range = cancer_filters.get('date_range', [])
        if date_range and len(date_range) == 2:
            if date_range[0]:
                params['date_from'] = date_range[0]
            if date_range[1]:
                params['date_to'] = date_range[1]
        cancer_types = cancer_filters.get('cancer_types', [])
        if cancer_types and len(cancer_types) == 1:
            params['cancer_type'] = cancer_types[0]
        return params

    def post(self, request):
        raw_filters = request.data.get('filters', {})
        options = request.data.get('options', {})
        images = request.data.get('images', {})
        filters = self._normalize_filters(raw_filters)

        # 1. Gather all statistics data from StatisticsViewSet
        stats_data = _make_internal_request(
            request,
            lambda d: RequestFactory().get('/api/cancers/statistics/report_summary/', data=d),
            StatisticsViewSet.as_view({'get': 'report_summary'}),
            filters
        )

        selected_charts = options.get('charts', [])

        # 2. Gather GIS analysis data (zone-based) — only if user wants chart/map
        gis_data = None
        if 'map' in selected_charts or 'bar' in selected_charts:
            gis_data = _make_internal_request(
                request,
                lambda d: RequestFactory().post('/api/gis/analyze/', data=json.dumps(d), content_type='application/json'),
                GisAnalyzeView,
                raw_filters
            )

        # 3. Setup PDF Generator
        buffer = io.BytesIO()
        title = options.get('title', "Rapport d'Analyse Épidémiologique")
        generator = PDFReportGenerator(buffer, title=title)

        generator.add_cover_page()

        # ── Section 1: Executive Summary KPIs ──
        if 'kpi' in selected_charts and stats_data and stats_data.get('kpi'):
            generator.add_kpi_section(stats_data['kpi'])

        # ── Section 2: Temporal Trends ──
        if 'temporal' in selected_charts and stats_data and stats_data.get('temporal'):
            generator.add_temporal_section(stats_data['temporal'])

        # ── Section 3: Cancer Distribution (includes stage) ──
        if 'distribution' in selected_charts:
            if stats_data and stats_data.get('cancer_distribution'):
                generator.add_cancer_distribution_section(stats_data['cancer_distribution'])
            if stats_data and stats_data.get('kpi', {}).get('stage_distribution'):
                generator.add_stage_distribution_section(stats_data['kpi']['stage_distribution'])

        # ── Section 4: Treatment Analysis ──
        if 'treatment' in selected_charts and stats_data and stats_data.get('treatment'):
            generator.add_treatment_section(stats_data['treatment'])

        # ── Section 5: Follow-Up Analysis ──
        if 'followup' in selected_charts and stats_data and stats_data.get('followup'):
            generator.add_followup_section(stats_data['followup'])

        # ── Section 6: Geographic Analysis ──
        if gis_data:
            zones_data = gis_data.get('zones', [])
            if zones_data:
                generator.add_section("Analyse Géographique par Zone")
                total_cases = gis_data.get('total_filtered_cases', 0)
                generator.add_paragraph(f"Analyse basée sur {total_cases} cas filtrés, répartis par zone géographique.")
                summary_table = []
                for z in zones_data:
                    summary_table.append([
                        z['zone_name'],
                        str(z['incidence']),
                        f"{z['mortality_rate']}%",
                        f"{z['pollution_level']} µg/m³" if z.get('pollution_level') else "—"
                    ])
                generator.add_table(summary_table, header=["Zone / Couche", "Cas (N)", "Taux Mortalité", "Pollution"])

        # Section: Geographic Coverage (from statistics)
        if stats_data and stats_data.get('geographic'):
            generator.add_geographic_section(stats_data['geographic'])

        # Section: Map Screenshot (if provided by frontend)
        if 'map' in selected_charts and images.get('map'):
            generator.add_section("Carte de Répartition")
            generator.add_paragraph("Répartition géographique des cas sur la carte.")
            generator.add_image_from_base64(images['map'])

        # ── Section 7: Mortality Analysis ──
        if 'mortality' in selected_charts and stats_data and stats_data.get('mortality', {}).get('results'):
            generator.add_mortality_section(stats_data['mortality'])

        # ── Section 8: Data Quality ──
        if 'data_quality' in selected_charts and stats_data and stats_data.get('documents'):
            generator.add_data_quality_section(stats_data['documents'])

        # Final Build
        generator.build()
        buffer.seek(0)

        filename = f"rapport_cancer_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
