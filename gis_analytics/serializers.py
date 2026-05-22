from rest_framework import serializers
from .models import Zone, ZoneDataSource, AreaLayer


class ZoneDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneDataSource
        fields = ['id', 'zone', 'pollution_level', 'population', 'year']


class ZoneSerializer(serializers.ModelSerializer):
    data_sources = ZoneDataSourceSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.prenom} {obj.created_by.nom}"
        return None

    class Meta:
        model = Zone
        fields = [
            'id', 'name', 'type', 'geojson',
            'created_by', 'created_by_name',
            'created_at', 'data_sources',
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'created_by_name']


class ZoneListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view — omits geojson + data_sources."""
    class Meta:
        model = Zone
        fields = ['id', 'name', 'type', 'created_at']


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
