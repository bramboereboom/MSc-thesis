import geopandas as gpd
import pandas as pd

gdf = gpd.read_file(r"C:\Users\bruno\Downloads\wegen_klein.geojson")

gdf = pd.concat([gdf[gdf['wegbehsrt'] == 'R'], gdf[gdf['wegbehsrt'] == 'P']])

gdf.to_file('snelwegen_provincie.shp')
