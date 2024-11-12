import folium as fo
import polars as pl 

hospody = pl.read_excel("hospody.xlsx")
hospody = hospody.filter(pl.col("Latitude").is_not_null() & pl.col("Longitude").is_not_null())

min_lat, max_lat = 50.6, 50.7
min_long, max_long = 14.0, 14.1

usti_map = fo.Map(
    location=[50.6617, 14.0434],  
    zoom_start=15,              
    max_bounds=True,            
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_long,
    max_lon=max_long,
    width="100%",
    height="100vh"
)

for row in hospody.to_dicts():
    název_hospody = row["Název"]
    lat = row["Latitude"]
    long = row["Longitude"]

    popup_content = f"<strong>{název_hospody}</strong>"

    fo.Marker(
        location=[lat, long],
        popup=fo.Popup(popup_content, max_width=300),
        icon=fo.Icon(icon="cocktail", color="lightgray", prefix="fa", icon_color="black")
    ).add_to(usti_map)

usti_map.save("usti_map.html")

