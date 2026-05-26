"""
Spatial analysis services for GIS analytics.

Uses shapely for point-in-polygon containment.
This avoids the GDAL/PostGIS system dependency on Windows,
while providing the same geometric precision.
"""
import json
import logging

logger = logging.getLogger(__name__)

try:
    from shapely.geometry import shape, Point
    from shapely.errors import ShapelyError
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    logger.warning(
        "shapely is not installed. Spatial analysis will be disabled. "
        "Run: pip install shapely"
    )


def _normalize_geojson(geojson) -> dict | None:
    """
    Normalize a GeoJSON value into a raw geometry dict.
    Accepts: string, dict geometry, Feature, or FeatureCollection.
    Returns: geometry dict or None on failure.
    """
    try:
        if isinstance(geojson, str):
            geojson = json.loads(geojson)

        if not isinstance(geojson, dict):
            return None

        geo_type = geojson.get('type')

        if geo_type == 'FeatureCollection':
            features = geojson.get('features', [])
            if not features:
                return None
            return features[0].get('geometry')

        if geo_type == 'Feature':
            return geojson.get('geometry')

        # Already a geometry (Polygon, MultiPolygon, etc.)
        return geojson

    except (json.JSONDecodeError, AttributeError, KeyError):
        return None


def point_in_zone(latitude: float, longitude: float, geojson) -> bool:
    """
    Return True if the (lat, lng) point is inside the GeoJSON polygon.

    Note: GeoJSON uses [longitude, latitude] coordinate order (RFC 7946).
          Shapely Point(x, y) maps to Point(longitude, latitude).

    Args:
        latitude: Patient latitude (float)
        longitude: Patient longitude (float)
        geojson: Zone geometry (dict, str, Feature, or FeatureCollection)

    Returns:
        bool: True if the point is within or on the boundary of the polygon.
    """
    if not SHAPELY_AVAILABLE:
        return False

    if latitude is None or longitude is None:
        return False

    geometry = _normalize_geojson(geojson)
    if geometry is None:
        return False

    try:
        polygon = shape(geometry)
        # Point(longitude, latitude) to match GeoJSON [lng, lat] order
        point = Point(float(longitude), float(latitude))
        return polygon.contains(point) or polygon.touches(point)
    except (ShapelyError, ValueError, TypeError) as e:
        logger.debug(f"point_in_zone geometry error: {e}")
        return False


def geometry_intersects_geojson(geom_a: dict, geom_b: dict) -> bool:
    """
    Return True if two GeoJSON geometry dicts spatially intersect.

    Args:
        geom_a: First GeoJSON geometry dict (e.g., user-drawn zone)
        geom_b: Second GeoJSON geometry dict (e.g., commune boundary)

    Returns:
        bool: True if the two geometries intersect or one contains the other.
    """
    if not SHAPELY_AVAILABLE:
        return False

    a = _normalize_geojson(geom_a)
    b = _normalize_geojson(geom_b)
    if a is None or b is None:
        return False

    try:
        poly_a = shape(a)
        poly_b = shape(b)
        return poly_a.intersects(poly_b) or poly_a.contains(poly_b) or poly_b.contains(poly_a)
    except (ShapelyError, ValueError, TypeError) as e:
        logger.debug(f"geometry_intersects_geojson error: {e}")
        return False
