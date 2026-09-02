from typing import Optional, Dict, Any

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping


def geom_to_geojson(geom) -> Optional[Dict[str, Any]]:
    """Convert a GeoAlchemy2 geometry column value into a plain GeoJSON dict."""
    if geom is None:
        return None
    return mapping(to_shape(geom))
