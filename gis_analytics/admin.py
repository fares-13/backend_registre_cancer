from django.contrib import admin
from .models import Zone, ZoneDataSource


class ZoneDataSourceInline(admin.TabularInline):
    model = ZoneDataSource
    extra = 1
    fields = ['year', 'pollution_level', 'population']


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display  = ['name', 'type', 'created_by', 'created_at']
    list_filter   = ['type', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines       = [ZoneDataSourceInline]


@admin.register(ZoneDataSource)
class ZoneDataSourceAdmin(admin.ModelAdmin):
    list_display = ['zone', 'year', 'pollution_level', 'population']
    list_filter  = ['year']
