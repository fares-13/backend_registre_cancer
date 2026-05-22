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

    def build(self):
        self.doc.build(self.elements)
