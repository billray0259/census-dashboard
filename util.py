def get_utm_epsg(lat, lon):
    """Return the EPSG code for the UTM zone corresponding to lat/lon."""
    zone = int((lon + 180) // 6) + 1
    if lat >= 0:
        epsg = 32600 + zone  # Northern Hemisphere
    else:
        epsg = 32700 + zone  # Southern Hemisphere
    return epsg