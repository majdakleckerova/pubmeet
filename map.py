import folium as fo

min_lat, max_lat = 50.6, 50.7
min_long, max_long = 14.0, 14.1

usti_map = fo.Map(
    location=[50.661, 14.041],  
    zoom_start=13,              
    max_bounds=True,           
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_long,
    max_lon=max_long
)

usti_map.save("usti_map.html")