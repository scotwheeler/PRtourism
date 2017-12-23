# -*- coding: utf-8 -*-
"""
TouristVeronoiMap
Setup

Created on Fri Sep 15 10:32:59 2017

@author: Scot Wheeler
"""

from os import path
import numpy as np
import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import cartopy.io.shapereader as csh
from VoronoiMapping import voronoi_polygons
from lxml import html, etree

__version__ = 2.0

shapefile_folder = path.normpath("shapefiles")


def import_shapefile(filename):
    """
    Imports shapefile and returns a GeoDataFrame
    """
    if filename[-4:] != ".shp":
        filename = filename + ".shp"
    filepath = path.join(shapefile_folder, filename)
    geo_df = gpd.read_file(filepath)
    return geo_df


def parkrun_locs_xml2csv(geo_doc="parkrun_geo.xml", country_code=97):
    """
    Get parkrun geolocations from
    http://www.parkrun.org.uk/wp-content/themes/parkrun/xml/geo.xml

    As parkrun doesn't allow scraping of data, save website as xml document

    Output
    ------
    csv with parkrun name, lat, long
    """
    # dont think parkrun lets you scrape this page
#    website = "http://www.parkrun.org.uk\
#    /wp-content/themes/parkrun/xml/geo.xml"
    tree = etree.parse(geo_doc)
    all_geo = pd.DataFrame([])
    for elt in tree.getiterator():
        elt_dict = dict(elt.items())
        elt_df = pd.DataFrame(dict(elt.items()), index=[0])
        all_geo = all_geo.append(elt_df, ignore_index=True)

    # select only parkruns, defined by having a c attribute
    all_parkruns = all_geo[pd.notnull(all_geo["c"])]

    # convert strings to numbers
    all_parkruns = all_parkruns.apply(pd.to_numeric, errors='ignore')

    # drop columns with all nan, these coloumns are for countries and regions
    all_parkruns = all_parkruns.dropna(axis=1, how="all")

    # reset index
    all_parkruns.reset_index(drop=True, inplace=True)

    all_parkruns.to_csv("world_parkruns.csv", index=False)

    uk_parkruns = all_parkruns[all_parkruns["c"] == 97]

    # remove channel islands and isle of man
    # need a better coastline whcih includes islands
    # for want of a better way
    for run in ["jersey", "guernsey", "nobles"]:
        uk_parkruns = uk_parkruns[uk_parkruns["n"] != run]

    uk_parkruns.reset_index(drop=True, inplace=True)
    uk_parkruns.to_csv("uk_parkruns.csv", index=False)

    return uk_parkruns


def create_parkrun_point_shp(filename="uk_parkruns", new_XML = True):
    """
    Creates a shapefile containing all parkrun point locations

    Input
    -----
    filename: str
        filename to csv file containing parkrun location data
        extracted from xml map on course page
        http://www.parkrun.org.uk/wp-content/themes/parkrun/xml/geo.xml

    Output
    ------
    Shapefile
    """
    # create the csv?
    if new_XML:
        parkrun_locs_xml2csv(geo_doc="parkrun_geo.xml", country_code=97)
    # define file names
    if filename[-4:] == ".csv":
        filename = filename[0:-4]
    input_csv = filename + ".csv"
    output_shp_filename = path.normpath(filename + ".shp")
    output_GPKG_filename = path.normpath(filename + ".GPKG")  # geopackage
    
    output_shp = path.join(shapefile_folder, output_shp_filename)
    output_GPKG = path.join(shapefile_folder, output_GPKG_filename)

    # import data
    parkruns = pd.read_csv(input_csv, engine='python')
    # an issue with an apostrophe, using python engine fixed

    # setup geodataframe
    parkruns["geometry"] = None  # create geometry column
    parkruns["m2"] = None  # second name column to remove Park
    for index, parkrun in parkruns.iterrows():
        prun_point = Point((parkrun["lo"], parkrun["la"]))
        parkruns.loc[index, "geometry"] = prun_point  # assign point to geom
        name2 = parkruns.loc[index, "m"].replace(" Park", "")  # remove Park
        # can't remember why Park is removed, maybe inconsistent with runners
        # profile
        parkruns.loc[index, "m2"] = name2

    # create geodataframe
    parkruns_geo = gpd.GeoDataFrame(parkruns)
    # geographic coordinate system
    parkruns_geo.crs = from_epsg(4326)  # set WGS84 (decimal degrees)
    # save as shapefile
    parkruns_geo.to_file(output_shp)

    # save to geopackage file
    parkruns_geo.to_file(output_GPKG)
    return parkruns_geo


def get_country_natural_earth_new(country_code=["GBR"]):
    """
    To do:
    Needs recoding for multiple countries.

    Input
    -----
    country_code: str
        The UN? country code for desired country

    Output
    ------
    geodataframe of all polygons making up the country in WGS84 projection
    """
    shpfilename = csh.natural_earth(resolution='10m', category='cultural',
                                    name='admin_0_countries')

    all_countries_gdf = gpd.read_file(shpfilename)

#    country_gdf_multi = all_countries_gdf[all_countries_gdf["ISO_A3"] ==\
#                         country_code]
    country_gdf_multi = all_countries_gdf[all_countries_gdf["ISO_A3"].isin(country_code)]
    country_gdf_multi = country_gdf_multi.reset_index(drop=True)
    # unzip the multipolygon of islands
#    country_gdf = gpd.GeoDataFrame({"geometry":list(country_gdf_multi["geometry"][0].geoms)})

    country_gdf = gpd.GeoDataFrame()
    for i, country in country_gdf_multi.iterrows():
        try:
#            country_gdf = country_gdf.append({"geometry":country_gdf_multi.loc[i, "geometry"]}, ignore_index=True)
            country_gdf = country_gdf.append({"geometry":list(country_gdf_multi.loc[i, "geometry"].geoms)}, ignore_index=True)
        except:
#            country_gdf = country_gdf.append({"geometry":list(country_gdf_multi.loc[i, "geometry"].geoms)}, ignore_index=True)
            country_gdf = country_gdf.append({"geometry":country_gdf_multi.loc[i, "geometry"]}, ignore_index=True)

    country_gdf.crs = from_epsg(4326) # ? projected coordinate system
    country_gdf_multi.crs = from_epsg(4326) # ? projected coordinate system
    return country_gdf, country_gdf_multi

def get_country_natural_earth(country_code="GBR"):
    """
    Get country natural earth map

    Input
    -----
    country_code: str
        The UN? country code for desired country

    Output
    ------
    geodataframe of all polygons making up the country in WGS84 projection
    """
    shpfilename = csh.natural_earth(resolution='10m', category='cultural',
                                    name='admin_0_countries')

    all_countries_gdf = gpd.read_file(shpfilename)

    country_gdf_multi = all_countries_gdf[
            all_countries_gdf["ISO_A3"] == country_code]

    country_gdf_multi = country_gdf_multi.reset_index(drop=True)
    # unzip the multipolygon of islands
    country_gdf = gpd.GeoDataFrame(
            {"geometry": list(country_gdf_multi["geometry"][0].geoms)})

    country_gdf.crs = from_epsg(4326)  # ? projected coordinate system
    country_gdf_multi.crs = from_epsg(4326)  # ? projected coordinate system
    return country_gdf, country_gdf_multi


def assign_parkrun_areas(uk_parkrun_points, uk_parkrun_voronoi, uk_map,
                         buffer=0.001*0.99,
                         filename="uk_parkrun_areas"):
    """
    Crops the raw voronoi diagram to the shape of the uk, and matches each area
    to it's corresponding parkrun.

    Input
    -----
    uk_parkrun_points: GeoDataFrame
        The point locations of UK parkruns with WGS84 (decimal degree)
        projection

    uk_parkrun_voronoi: GeoDataFrame
        Voronoi diagram of UK parkruns, generated using voronoi_polygons2.
        WGS84 (decimal degree) projection

    uk_map: GeoDataFrame
        Natural earth country output GeoDatafFrame imported using
        get_country_geo_df. In the case of the UK, geometry will contain a
        multipolygon of each island.

    buffer: float
        The intial distance (decimal degrees) to increase the map size by.

    Returns
    -------
    GeoDataFrame of shapely polygons for parkrun areas (decimal degrees)
    """

    uk_geo_df = uk_map.copy()

    # column to count parkruns on each island
    uk_geo_df["number"] = 0

    uk_parkrun_points_areas = uk_parkrun_points.copy()

    # column for island index of each run
    uk_parkrun_points_areas["map_index"] = None

    # Assign each parkrun with a uk island map index.
    # Because the current uk map resolution isn't good enough, some parkrun
    # locations are off the map. As a quick fix, using buffer to increase the
    # size of the uk. This is increased by 0.1% until all parkruns are
    # accounted for.
    while (uk_geo_df["number"].sum()) < (len(uk_parkrun_points["geometry"])):
        for index, uk_area in enumerate(uk_geo_df["geometry"]):
            # because uk map isn't accurate enough to contain all coastal
            # there is a risk an island may overlap with mainland parkrun?
            # buffer each island
            uk_geo_df.loc[index, "geometry"] = uk_area.buffer(buffer)

        # count number of parkruns in each uk area
        for index, uk_area in enumerate(uk_geo_df["geometry"]):
            parkrun_points = []  # add parkrun id to, then use length
            # for each parkrun, check if within uk area
            for index2, point in enumerate(uk_parkrun_points["geometry"]):
                if point.within(uk_area):
                    parkrun_points.append(uk_parkrun_points.loc[index2, "id"])
                    # assign map index to areas df
                    uk_parkrun_points_areas.loc[index2, "map_index"] = index
            uk_geo_df.loc[index, "number"] = len(parkrun_points)
        buffer*=1.001  # 1% increase in buffer
    print(buffer)

    # Create a new GeoDataFrame for the area polygons, as GeoDataFrame can't
    # have 2 geometry columns. Must separate points and areas.
    uk_parkrun_areas = uk_parkrun_points_areas.copy()
    cropped_areas = uk_parkrun_voronoi.copy()
    ghost_areas = []  # to collect areas separated by eg rivers from closest

    # For each point, check if within each voronoi polygon.
    # If it is the only parkrun within that map island, set the map island as
    # the parkrun area
    # Else, set the overlap of the voronoi and map polygons as the parkrun area
    # Try to append to uk_parkrun_areas, error if multiple polygon, this is
    # caused if say a river in the uk map cuts the voronoi polygon into more
    # than one piece. As a quick fix, take the largest polygon.
    for point_index, point in enumerate(uk_parkrun_points_areas["geometry"]):
        for vor_poly_index, vor_poly in enumerate(
                uk_parkrun_voronoi["geometry"]):
            # is point within voronoi polygon
            if point.within(vor_poly):
                # now find associatated island
                map_index = uk_parkrun_points_areas.loc[point_index,
                                                        "map_index"]
                uk_island = uk_geo_df.loc[map_index, "geometry"]
                # is it the only parkrun for that island
                if uk_geo_df.loc[map_index, "number"] == 1:
                    # only one parkrun on an island. ie Medina IoW
                    new_poly = uk_island
                else:
                    if vor_poly.intersects(uk_island):
                        # crop voronoi polygon to island coast
                        new_poly = vor_poly.intersection(uk_island)
                    else:
                        print(uk_parkrun_points_areas.loc[point_index, "m"])

                cropped_areas.loc[vor_poly_index, "geometry"] = new_poly
                # might have created a multipolygon with a river for instance
                if new_poly.geom_type == "Polygon":
                    uk_parkrun_areas.loc[point_index, "geometry"] = new_poly
                elif new_poly.geom_type == "MultiPolygon":
                    # need to deal with multiple polygons a better way.
                    largest = Point((0, 0))
                    for polyyyy in new_poly:
                        # could use the largest polygon area, not ideal
#                        if abs(polyyyy.area) > abs(largest.area):
#                            largest = polyyyy
#                    uk_parkrun_areas.loc[point_index, "geometry"] = largest
                        # or whichever contains the parkrun location
                        if polyyyy.contains(point):
                            uk_parkrun_areas.loc[point_index,
                                                 "geometry"] = polyyyy
                        else:
                            ghost_areas.append(polyyyy)

                    # could try adding other areas to neighbours but hard to
                    # find
                else:
                    raise IOError("Shape is not a polygon")
                pass

    # calculate the area (in decimal degrees) for each parkrun
    uk_parkrun_areas["area"] = 0
    for index, row in uk_parkrun_areas.iterrows():
        uk_parkrun_areas.loc[index, "area"] = (
                uk_parkrun_areas.loc[index, "geometry"].area)

    # save files
    uk_parkrun_shp_filename = path.normpath(filename+".shp")
    uk_parkrun_shp_filepath = path.join(shapefile_folder,
                                        uk_parkrun_shp_filename)
    uk_parkrun_gpkg_filename = path.normpath(filename+".GPKG")
    uk_parkrun_gpkg_filepath = path.join(shapefile_folder,
                                         uk_parkrun_gpkg_filename)
    
    uk_parkrun_areas.to_file(uk_parkrun_shp_filepath)
    uk_parkrun_areas.to_file(uk_parkrun_gpkg_filepath)
    return uk_parkrun_areas


def setup():
    """
    Run this if new parkrun location data has been downloaded
    """
    # get parkrun locations
    uk_parkrun_points = create_parkrun_point_shp("uk_parkruns")
    # get country polygons
    uk_df, country_gdf_multi = get_country_natural_earth()
    # create a voronoi object
    uk_parkruns_voronoi = voronoi_polygons(uk_parkrun_points,
                                           country_gdf_multi)
    uk_parkrun_areas = assign_parkrun_areas(uk_parkrun_points,
                                            uk_parkruns_voronoi, uk_df,
                                            buffer=0.0056,
                                            filename="uk_parkrun_areas")

    return uk_parkrun_areas

if __name__ == "__main__":
    uk, uk2 = get_country_natural_earth()
    # run setup to regenerate UK parkrun veroni map
#    uk_parkrun_areas = setup()
#    uk_parkrun_areas.plot()
    pass

