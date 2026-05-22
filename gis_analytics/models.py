import uuid
from django.db import models
from accounts.models import Utilisateur


class Zone(models.Model):
    """
    Geographic zone defined by a GeoJSON polygon.
    Used to group patients and cancer cases spatially.
    """
    class ZoneType(models.TextChoices):
        POLLUTION    = 'pollution',    'Zone de Pollution'
        INDUSTRIAL   = 'industrial',   'Zone Industrielle'
        ADMINISTRATIVE = 'administrative', 'Zone Administrative'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nom de la zone")
    type = models.CharField(
        max_length=20,
        choices=ZoneType.choices,
        default=ZoneType.ADMINISTRATIVE,
        verbose_name="Type de zone",
    )
    # GeoJSON geometry object (Polygon or MultiPolygon).
    # Format: {"type": "Polygon", "coordinates": [[[lng, lat], ...]]}
    geojson = models.JSONField(
        verbose_name="Géométrie GeoJSON",
        help_text=(
            'Polygon GeoJSON geometry. Example: '
            '{"type": "Polygon", "coordinates": [[[lng, lat], ...]]}'
        ),
    )
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='zones_created',
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    class Meta:
        verbose_name = "Zone"
        verbose_name_plural = "Zones"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type'], name='zone_type_idx'),
        ]


class ZoneDataSource(models.Model):
    """
    Yearly environmental / demographic data for a zone.
    Used to enrich analytics with pollution levels and population.
    """
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='data_sources',
        verbose_name="Zone",
    )
    pollution_level = models.FloatField(
        null=True, blank=True,
        verbose_name="Niveau de pollution (µg/m³)",
    )
    population = models.IntegerField(
        null=True, blank=True,
        verbose_name="Population estimée",
    )
    year = models.IntegerField(verbose_name="Année")

    def __str__(self):
        return f"{self.zone.name} — {self.year}"

    class Meta:
        verbose_name = "Source de Données Zone"
        verbose_name_plural = "Sources de Données Zones"
        ordering = ['-year']
        unique_together = ('zone', 'year')


class AreaLayer(models.Model):
    """
    Manually defined spatial classification layer for map coloring and overlay.
    Architect role creates these to highlight regions (communes/wilayas).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Titre de la couche")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    color = models.CharField(max_length=50, default="#ff0000", verbose_name="Couleur d'affichage")
    regions = models.JSONField(
        default=list,
        verbose_name="Régions sélectionnées",
        help_text="Liste des noms de communes/wilayas inclus dans cette couche."
    )
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='area_layers_created',
        verbose_name="Créé par (Architecte)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Couche Spatiale (AreaLayer)"
        verbose_name_plural = "Couches Spatiales (AreaLayers)"
        ordering = ['-created_at']

