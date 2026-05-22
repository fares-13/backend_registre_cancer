import io
import json
from datetime import datetime
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response

from .services import PDFReportGenerator
from gis_analytics.views import GisAnalyzeView

class ReportGenerateView(APIView):
    """
    POST /api/reports/generate/
    
    Generates a PDF report based on filters and optional chart snapshots.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        filters = request.data.get('filters', {})
        options = request.data.get('options', {})
        images  = request.data.get('images', {})

        # 1. Reuse GIS analysis to get the data
        # We use as_view() and pass a proper DRF request simulation
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Create a basic django request
        django_request = factory.post('/api/gis/analyze/', data=json.dumps(filters), content_type='application/json')
        
        # Copy the authorization header so the internal view passes JWT authentication
        if 'HTTP_AUTHORIZATION' in request.META:
            django_request.META['HTTP_AUTHORIZATION'] = request.META['HTTP_AUTHORIZATION']
        elif 'HTTP_AUTHORIZATION' in request._request.META:
            django_request.META['HTTP_AUTHORIZATION'] = request._request.META['HTTP_AUTHORIZATION']
            
        django_request.user = request.user
        
        # Call the view
        gis_view = GisAnalyzeView.as_view()
        gis_response = gis_view(django_request)
        
        if gis_response.status_code != 200:
            return Response(gis_response.data, status=gis_response.status_code)
        
        analysis_data = gis_response.data
        zones_data = analysis_data.get('zones', [])

        # 2. Setup PDF Generation
        buffer = io.BytesIO()
        title = options.get('title', "Rapport d'Analyse Épidémiologique")
        generator = PDFReportGenerator(buffer, title=title)

        # 3. Build Content
        generator.add_cover_page()

        # Section: Dashboard Summary
        generator.add_section("Résumé Global")
        total_cases = analysis_data.get('total_filtered_cases', 0)
        generator.add_paragraph(f"Analyse basée sur un total de {total_cases} cas filtrés enregistrés dans le système.")
        
        # Summary Table
        metrics_selected = options.get('metrics', ['incidence', 'mortality'])
        if zones_data:
            summary_table_data = [] # Data rows
            header = ["Zone / Couche", "Cas (N)", "Taux Mortalité", "Pollution"]
            for z in zones_data:
                summary_table_data.append([
                    z['zone_name'],
                    str(z['incidence']),
                    f"{z['mortality_rate']}%",
                    f"{z['pollution_level']} µg/m³" if z['pollution_level'] else "—"
                ])
            generator.add_table(summary_table_data, header=header)

        # Section: Geographic Distribution
        if 'map' in options.get('charts', []) and images.get('map'):
            generator.add_section("Analyse Cartographique")
            generator.add_paragraph("Répartition géographique de l'incidence par zone géographique définie.")
            generator.add_image_from_base64(images['map'])

        # Section: Statistical Charts
        if any(c in options.get('charts', []) for c in ['bar', 'pie', 'line_trend', 'pie_gender', 'bar_age']):
            generator.add_section("Analyses Statistiques")
            
            # Bar Chart: Incidence per Zone
            if 'bar' in options.get('charts', []):
                if images.get('bar'):
                    generator.add_paragraph("Incidence par zone (Capture écran)")
                    generator.add_image_from_base64(images['bar'])
                else:
                    generator.add_paragraph("Incidence par zone (Génération système)")
                    bar_data = [(z['zone_name'], z['incidence']) for z in zones_data]
                    generator.add_bar_chart(bar_data)
            
            # Pie Chart: Cancer Type Distribution
            if 'pie' in options.get('charts', []):
                generator.add_paragraph("Répartition par type de cancer (Génération système)")
                global_type_dist = {}
                for z in zones_data:
                    for t, count in z.get('cancer_type_distribution', {}).items():
                        global_type_dist[t] = global_type_dist.get(t, 0) + count
                
                pie_data = list(global_type_dist.items())
                if pie_data:
                    generator.add_pie_chart(pie_data, title="Types de Cancer")

            # Line Chart: Temporal Trend
            if 'line_trend' in options.get('charts', []):
                generator.add_paragraph("Tendance Temporelle de l'Incidence (Génération système)")
                global_trend_dist = {}
                for z in zones_data:
                    for month, count in z.get('temporal_trend', {}).items():
                        global_trend_dist[month] = global_trend_dist.get(month, 0) + count
                
                trend_data = list(global_trend_dist.items())
                if trend_data:
                    generator.add_line_chart(trend_data, x_label="Mois/Année", y_label="Nouveaux Cas", title="Évolution Temporelle")

            # Pie Chart: Gender Distribution
            if 'pie_gender' in options.get('charts', []):
                generator.add_paragraph("Répartition par Sexe (Génération système)")
                males = sum(z.get('gender_distribution', {}).get('M', 0) for z in zones_data)
                females = sum(z.get('gender_distribution', {}).get('F', 0) for z in zones_data)
                gender_data = [('Hommes', males), ('Femmes', females)]
                if males > 0 or females > 0:
                    generator.add_pie_chart(gender_data, title="Répartition par Sexe")

            # Bar Chart: Age Distribution
            if 'bar_age' in options.get('charts', []):
                generator.add_paragraph("Distribution par Tranche d'Âge (Génération système)")
                global_age_dist = {}
                for z in zones_data:
                    for bracket, count in z.get('age_distribution', {}).items():
                        global_age_dist[bracket] = global_age_dist.get(bracket, 0) + count
                
                age_data = list(global_age_dist.items())
                if age_data:
                    # Specific order for age brackets
                    age_order = ['0-18', '19-35', '36-50', '51-65', '65+']
                    age_data.sort(key=lambda x: age_order.index(x[0]) if x[0] in age_order else 99)
                    generator.add_bar_chart(age_data, x_label="Tranche d'Âge", y_label="Nombre de Cas", title="Pyramide des Âges Simplifiée", color="#f59e0b")        # Final Build
        generator.build()
        buffer.seek(0)
        
        filename = f"rapport_cancer_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
