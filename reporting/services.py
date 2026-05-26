import io
import base64
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
from django.conf import settings

class PDFReportGenerator:
    """
    Service to generate professional epidemiological PDF reports
    using reportlab.
    """
    def __init__(self, buffer, title="Rapport Épidémiologique"):
        self.buffer = buffer
        self.doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.elements = []
        self.title = title

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor("#1e293b")
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            leading=20,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor("#3b82f6"),
            borderPadding=5,
        ))
        self.styles.add(ParagraphStyle(
            name='StatLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='StatValue',
            parent=self.styles['Normal'],
            fontSize=14,
            fontWeight='bold',
            alignment=TA_CENTER,
            spaceAfter=10
        ))

    def add_cover_page(self, registry_name="Registre de Cancer - Tlemcen"):
        self.elements.append(Spacer(1, 5*cm))
        self.elements.append(Paragraph(registry_name, self.styles['ReportTitle']))
        self.elements.append(Spacer(1, 1*cm))
        self.elements.append(Paragraph(self.title, self.styles['Heading2']))
        self.elements.append(Spacer(1, 2*cm))
        self.elements.append(Paragraph(f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}", self.styles['Normal']))
        self.elements.append(PageBreak())

    def add_section(self, title):
        self.elements.append(Paragraph(title, self.styles['SectionHeader']))

    def add_paragraph(self, text, style_name='Normal'):
        self.elements.append(Paragraph(text, self.styles[style_name]))
        self.elements.append(Spacer(1, 0.5*cm))

    def add_image_from_base64(self, base64_str, width=15*cm):
        """Decode base64 string and add it as an image to the document."""
        if not base64_str:
            return
        
        try:
            # Handle data:image/png;base64, prefix if present
            if ';base64,' in base64_str:
                base64_str = base64_str.split(';base64,')[1]
            
            img_data = base64.b64decode(base64_str)
            img_buffer = io.BytesIO(img_data)
            img = Image(img_buffer)
            
            # Maintain aspect ratio
            aspect = img.imageHeight / img.imageWidth
            img.drawHeight = width * aspect
            img.drawWidth = width
            
            self.elements.append(img)
            self.elements.append(Spacer(1, 0.5*cm))
        except Exception as e:
            self.add_paragraph(f"[Erreur lors de l'insertion de l'image : {str(e)}]", 'Normal')

    def add_table(self, data, header=None):
        if header:
            data.insert(0, header)
        
        t = Table(data, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        self.elements.append(t)
        self.elements.append(Spacer(1, 1*cm))

    def add_line_chart(self, data, x_label="Mois", y_label="Cas", title="Tendance Temporelle", color="#10b981"):
        """Generate a line chart using matplotlib and add it to the PDF."""
        try:
            # Sort data by the x-axis (month keys)
            data_sorted = sorted(data, key=lambda x: x[0])
            names = [d[0] for d in data_sorted]
            values = [d[1] for d in data_sorted]
            
            plt.figure(figsize=(10, 6))
            plt.plot(names, values, marker='o', linestyle='-', color=color, linewidth=2)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.title(title)
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150)
            plt.close()
            img_buffer.seek(0)
            
            img = Image(img_buffer)
            width = 15*cm
            img.drawWidth = width
            img.drawHeight = width * 0.6
            
            self.elements.append(img)
            self.elements.append(Spacer(1, 1*cm))
        except Exception as e:
            self.add_paragraph(f"[Erreur génération Line Chart : {str(e)}]", 'Normal')

    def add_bar_chart(self, data, x_label="Catégorie", y_label="Cas", title="Distribution", color="#3b82f6"):
        """Generate a bar chart using matplotlib and add it to the PDF."""
        try:
            names = [d[0] for d in data]
            values = [d[1] for d in data]
            
            plt.figure(figsize=(10, 6))
            bars = plt.bar(names, values, color=color)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.title(title)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save to BytesIO
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150)
            plt.close()
            img_buffer.seek(0)
            
            img = Image(img_buffer)
            # Maintain aspect ratio (10:6)
            width = 15*cm
            img.drawWidth = width
            img.drawHeight = width * 0.6
            
            self.elements.append(img)
            self.elements.append(Spacer(1, 1*cm))
        except Exception as e:
            self.add_paragraph(f"[Erreur génération Bar Chart : {str(e)}]", 'Normal')

    def add_pie_chart(self, data, title="Répartition par Type"):
        """Generate a pie chart using matplotlib and add it to the PDF."""
        try:
            labels = [d[0] for d in data]
            values = [d[1] for d in data]
            
            plt.figure(figsize=(8, 8))
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired(range(len(labels))))
            plt.title(title)
            plt.tight_layout()
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150)
            plt.close()
            img_buffer.seek(0)
            
            img = Image(img_buffer)
            width = 12*cm
            img.drawWidth = width
            img.drawHeight = width
            
            self.elements.append(img)
            self.elements.append(Spacer(1, 1*cm))
        except Exception as e:
            self.add_paragraph(f"[Erreur génération Pie Chart : {str(e)}]", 'Normal')

    # ── Executive Summary KPI Section ──
    def add_kpi_section(self, kpi_data):
        self.add_section("Résumé Exécutif — Indicateurs Clés")
        self.add_paragraph("Synthèse des indicateurs épidémiologiques pour la période et les filtres sélectionnés.")
        d = kpi_data
        rows = [
            ["Patients enregistrés", str(d.get('total_patients', 0)), "Cas total", str(d.get('total_cases', 0))],
            ["Cas ce mois-ci", str(d.get('cases_this_month', 0)), "Cas actifs", str(d.get('active_cases', 0))],
            ["Décès", str(d.get('deceased', 0)), "Taux mortalité", f"{d.get('mortality_rate', 0)}%"],
            ["Taux survie", f"{d.get('survival_rate', 0)}%", "Récurrence", f"{d.get('recurrence_rate', 0)}%"],
            ["Âge moyen", f"{d.get('avg_age', '—')} ans", "Hommes", str(d.get('total_male', 0))],
            ["Femmes", str(d.get('total_female', 0)), "Suivis actifs", str(d.get('active_followups', 0))],
            ["Perdus de vue", str(d.get('lost_followup', 0)), "Patients pédiatriques", str(d.get('pediatric_count', 0))],
            ["Patients adultes", str(d.get('adult_count', 0)), "", ""],
        ]
        self.add_table(rows, header=["Indicateur", "Valeur", "Indicateur", "Valeur"])

    # ── Temporal Trends Section ──
    def add_temporal_section(self, temporal_data):
        self.add_section("Évolution Temporelle")
        monthly = temporal_data.get('monthly', [])
        yearly = temporal_data.get('yearly', [])
        mortality_monthly = temporal_data.get('mortality_monthly', [])

        if yearly:
            self.add_paragraph("Tendance annuelle des nouveaux cas.")
            yr_data = [(str(y['year']), y['count']) for y in yearly]
            self.add_line_chart(yr_data, x_label="Année", y_label="Nouveaux Cas", title="Évolution Annuelle des Cas", color="#3b82f6")

            yr_table = [[str(y['year']), str(y['count'])] for y in yearly]
            self.add_table(yr_table, header=["Année", "Nombre de Cas"])

        if monthly:
            self.add_paragraph("Distribution mensuelle des cas.")
            mo_data = [(m['month'][:7], m['count']) for m in monthly[-24:]]
            self.add_bar_chart(mo_data, x_label="Mois", y_label="Cas", title="Cas par Mois (24 derniers)", color="#10b981")

        if mortality_monthly:
            self.add_paragraph("Évolution mensuelle de la mortalité.")
            mort_data = [(m['month'][:7], m['count']) for m in mortality_monthly[-24:]]
            self.add_line_chart(mort_data, x_label="Mois", y_label="Décès", title="Mortalité Mensuelle", color="#ef4444")

    # ── Cancer Distribution Section ──
    def add_cancer_distribution_section(self, distribution_data):
        self.add_section("Distribution par Type de Cancer")
        by_type = distribution_data.get('by_type', [])
        by_type_sex = distribution_data.get('by_type_sex', [])
        by_age_group = distribution_data.get('by_age_group', [])

        if by_type:
            self.add_paragraph("Répartition des cas par type de cancer.")
            pie_data = [(t['name'], t['count']) for t in by_type]
            self.add_pie_chart(pie_data, title="Types de Cancer")
            type_table = [[t['name'], str(t['count']), f"{round(t['count']/max(sum(x['count'] for x in by_type),1)*100,1)}%"] for t in by_type]
            self.add_table(type_table, header=["Type de Cancer", "Cas", "Proportion"])

        if by_type_sex:
            self.add_paragraph("Distribution croisée Type de Cancer × Sexe.")
            merged = {}
            for t in by_type_sex:
                key = t['cancer_type']
                if key not in merged:
                    merged[key] = {'name': key, 'Masculin': 0, 'Féminin': 0}
                merged[key][t['sexe']] = merged[key].get(t['sexe'], 0) + t['count']
            stacked = list(merged.values())
            if stacked:
                self.add_stacked_bar_chart(stacked, x_label="Type de Cancer", y_label="Cas", title="Type × Sexe")

        if by_age_group:
            self.add_paragraph("Distribution par tranche d'âge.")
            age_order = ['0-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70+']
            age_data = sorted([(a['name'], a['count']) for a in by_age_group], key=lambda x: age_order.index(x[0]) if x[0] in age_order else 99)
            self.add_bar_chart(age_data, x_label="Tranche d'Âge", y_label="Cas", title="Pyramide des Âges", color="#f59e0b")

    # ── Stage Distribution Section ──
    def add_stage_distribution_section(self, stage_data):
        if not stage_data:
            return
        self.add_section("Répartition par Stade")
        self.add_paragraph("Classification des cas selon le stade au diagnostic.")
        stage_list = [(s['name'], s['count']) for s in stage_data]
        if stage_list:
            self.add_pie_chart(stage_list, title="Stades au Diagnostic")
            tot = max(sum(s[1] for s in stage_list), 1)
            stage_table = [[s[0], str(s[1]), f"{round(s[1]/tot*100,1)}%"] for s in stage_list]
            self.add_table(stage_table, header=["Stade", "Cas", "Proportion"])

    # ── Treatment Section ──
    def add_treatment_section(self, treatment_data):
        self.add_section("Analyse des Traitements")
        by_type = treatment_data.get('by_type', [])
        total = treatment_data.get('total_treatments', 0)
        with_tx = treatment_data.get('cases_with_treatment', 0)
        without_tx = treatment_data.get('cases_without_treatment', 0)

        self.add_paragraph(f"Total des traitements administrés : {total}. Cas avec traitement : {with_tx}, sans traitement : {without_tx}.")

        if by_type:
            pie_data = [(t['name'], t['count']) for t in by_type]
            self.add_pie_chart(pie_data, title="Types de Traitement")
            tx_table = [[t['name'], str(t['count']), f"{round(t['count']/max(total,1)*100,1)}%"] for t in by_type]
            self.add_table(tx_table, header=["Traitement", "Nombre", "Proportion"])

    # ── Follow-Up Analysis Section ──
    def add_followup_section(self, followup_data):
        self.add_section("Analyse du Suivi")
        d = followup_data
        self.add_paragraph("État des visites de suivi pour les cas inclus dans le rapport.")

        summary_rows = [
            ["Total suivis", str(d.get('total_followups', 0))],
            ["Cas avec suivi", str(d.get('cases_with_followup', 0))],
            ["Cas sans suivi", str(d.get('cases_without_followup', 0))],
            ["Suivis actifs", str(d.get('active_followups', 0))],
            ["Suivis en retard", str(d.get('overdue_followups', 0))],
            ["Perdus de vue", str(d.get('lost_to_followup', 0))],
        ]
        self.add_table(summary_rows, header=["Indicateur", "Valeur"])

        by_visit = d.get('by_visit_type', [])
        if by_visit:
            visit_data = [(v['name'], v['count']) for v in by_visit]
            self.add_bar_chart(visit_data, x_label="Type de Visite", y_label="Nombre", title="Types de Visites de Suivi", color="#14b8a6")

    # ── Data Quality Section ──
    def add_data_quality_section(self, document_data):
        self.add_section("Qualité des Données — Couverture Documentaire")
        d = document_data
        total = d.get('total_cases', 1) or 1
        items = [
            ("Imagerie", d.get('cases_with_imaging', 0), total, "#3b82f6"),
            ("Analyse Biologique", d.get('cases_with_analysis', 0), total, "#10b981"),
            ("Anatomopathologie", d.get('cases_with_anapath', 0), total, "#8b5cf6"),
            ("Marqueurs Moléculaires", d.get('cases_with_molecular', 0), total, "#f59e0b"),
        ]
        self.add_paragraph("Proportion de cas disposant de documents attachés par catégorie.")
        cov_table = [[label, str(val), f"{val}/{total}", f"{round(val/max(total,1)*100,1)}%"] for label, val, total, _ in items]
        self.add_table(cov_table, header=["Type de Document", "Cas avec doc.", "Total", "Couverture"])

        for label, val, tot, color in items:
            pct = round(val / max(tot, 1) * 100, 1)
            self._add_progress_bar(label, val, tot, pct, color)

    def _add_progress_bar(self, label, value, total, pct, color_hex):
        bar_width = 14 * cm
        bar_height = 0.6 * cm
        try:
            fig, ax = plt.subplots(figsize=(bar_width / cm, 0.8))
            ax.barh([0], [pct], height=0.6, color=color_hex, left=0)
            ax.set_xlim(0, 100)
            ax.axvline(0, color='black', linewidth=0)
            ax.set_yticks([])
            ax.set_xticks([0, 25, 50, 75, 100])
            ax.text(pct + 1, 0, f"{pct}%", va='center', fontsize=9, fontweight='bold')
            ax.set_title(f"{label}: {value}/{total}", fontsize=9, loc='left', fontweight='normal')
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(left=False, bottom=False, labelsize=8)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=120, transparent=True)
            plt.close()
            buf.seek(0)
            img = Image(buf)
            img.drawWidth = bar_width
            img.drawHeight = 0.8 * cm
            self.elements.append(img)
            self.elements.append(Spacer(1, 0.3 * cm))
        except Exception as e:
            self.add_paragraph(f"[Erreur barre de progression : {str(e)}]")

    # ── Mortality Section ──
    def add_mortality_section(self, mortality_data):
        self.add_section("Analyse de la Mortalité")
        results = mortality_data.get('results', [])
        count = mortality_data.get('count', 0)
        self.add_paragraph(f"Total des décès enregistrés : {count}. Détail des {len(results)} derniers cas.")
        if results:
            mort_table = []
            for r in results:
                types = ', '.join(r.get('cancer_types', []))[:60]
                cause = r.get('cause', '—')[:40]
                mort_table.append([
                    f"{r.get('nom', '')} {r.get('prenom', '')}",
                    r.get('sexe', '—'),
                    r.get('date_deces', '—')[:10] if r.get('date_deces') else '—',
                    cause,
                    types,
                ])
            self.add_table(mort_table, header=["Patient", "Sexe", "Date Décès", "Cause", "Types de Cancer"])

    # ── Geographic Section ──
    def add_geographic_section(self, geo_data):
        self.add_section("Couverture Géographique")
        with_c = geo_data.get('with_coordinates', 0)
        without_c = geo_data.get('without_coordinates', 0)
        rate = geo_data.get('coverage_rate', 0)
        total_g = geo_data.get('total_patients_geo', 0)
        self.add_paragraph(f"Total patients avec coordonnées géographiques : {with_c} / {total_g} ({rate}%). Patients sans coordonnées : {without_c}.")
        geo_table = [
            ["Avec coordonnées", str(with_c), f"{rate}%"],
            ["Sans coordonnées", str(without_c), f"{round(100-rate,1)}%"],
        ]
        if with_c > 0:
            self._add_progress_bar("Couverture géographique", with_c, total_g, round(rate, 1), "#6366f1")
        self.add_table(geo_table, header=["Catégorie", "Nombre", "Proportion"])

    # ── Stacked Bar Chart (type × sex) ──
    def add_stacked_bar_chart(self, data, x_label="Catégorie", y_label="Cas", title="Distribution Croisée"):
        try:
            names = [d['name'] for d in data]
            males = [d.get('Masculin', 0) for d in data]
            females = [d.get('Féminin', 0) for d in data]
            plt.figure(figsize=(10, 6))
            plt.bar(names, males, label='Hommes', color='#3b82f6')
            plt.bar(names, females, bottom=males, label='Femmes', color='#ec4899')
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.title(title)
            plt.xticks(rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            plt.close()
            buf.seek(0)
            img = Image(buf)
            width = 15 * cm
            img.drawWidth = width
            img.drawHeight = width * 0.6
            self.elements.append(img)
            self.elements.append(Spacer(1, 1 * cm))
        except Exception as e:
            self.add_paragraph(f"[Erreur Stacked Bar Chart : {str(e)}]")

    def build(self):
        self.doc.build(self.elements)
