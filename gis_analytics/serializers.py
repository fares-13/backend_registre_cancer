from rest_framework import serializers
from .models import Zone, ZoneGeometry, ZoneDataSource, AreaLayer, Commune


class ZoneDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneDataSource
        fields = ['id', 'zone', 'pollution_level', 'population', 'year']


class ZoneGeometrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneGeometry
        fields = ['id', 'geometry_type', 'geometry', 'created_at']
        read_only_fields = ['id', 'created_at']


class ZoneSerializer(serializers.ModelSerializer):
    data_sources = ZoneDataSourceSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    geometries = ZoneGeometrySerializer(many=True, read_only=True)

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.prenom} {obj.created_by.nom}"
        return None

    class Meta:
        model = Zone
        fields = [
            'id', 'name', 'description', 'color', 'type',
            'geojson', 'geometries',
            'created_by', 'created_by_name',
            'created_at', 'updated_at', 'data_sources',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'created_by_name']


class ZoneListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view."""
    geometry_count = serializers.SerializerMethodField()

    def get_geometry_count(self, obj):
        return obj.geometries.count()

    class Meta:
        model = Zone
        fields = ['id', 'name', 'description', 'color', 'type', 'created_at', 'geometry_count']


class ZoneCreateSerializer(serializers.ModelSerializer):
    """Simple serializer for zone creation — single geometry via geojson field."""
    geojson = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Zone
        fields = ['id', 'name', 'description', 'color', 'geojson', 'created_by']
        read_only_fields = ['id', 'created_by']

    def create(self, validated_data):
        return Zone.objects.create(**validated_data)


class AreaLayerSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.prenom} {obj.created_by.nom}"
        return None

    class Meta:
        model = AreaLayer
        fields = [
            'id', 'title', 'description', 'color', 'regions',
            'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'created_by_name']


class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commune
        fields = ['id', 'name', 'wilaya', 'geojson']
