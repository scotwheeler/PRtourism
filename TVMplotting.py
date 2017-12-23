"""
Tourist Voronoi Map
Plotting

Created on Fri Sep 15 13:44:58 2017

@author: Scot Wheeler
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
import bokeh.plotting as bk
from bokeh.models import (ColumnDataSource, HoverTool, Label)
from bokeh.tile_providers import CARTODBPOSITRON_RETINA as uk
import TVMsetup
import personal_parkrun
from os import path

__version__ = 2.0

shapefile_folder = path.normpath("shapefiles")
map_output_folder = path.normpath("maps")


def import_shapefile(filename):
    """
    Imports shapefile and returns a GeoDataFrame
    """
    if filename[-4:] != ".shp":
        filename = filename + ".shp"
    filepath = path.join(shapefile_folder, filename)
    geo_df = gpd.read_file(filepath)
    return geo_df


def convert_to_web_mercator(geo_df, cols=["geometry"]):
    # convert to mercator
    web_mercator_proj = geo_df.copy()
    for col in cols:
        web_mercator_proj[col] = web_mercator_proj[col].to_crs(epsg=3857)
    # confused over the projections
    # 3857 used by google maps but not a recognised geodetic system
    # 3395 is World Mercator
    web_mercator_proj.crs = from_epsg(3857)
#    web_mercator_proj.crs = from_epsg(3395)
    return web_mercator_proj


def getPoint_xy(row, coord):
    if coord == "x":
        return row["geometry"].x
    if coord == "y":
        return row["geometry"].y


def getPoly_xy(row, coord_type, cols="geometry"):
    """Returns the coordinates ('x' or 'y') of edges of a Polygon exterior"""

    # Parse the exterior of the coordinate
    exterior = row[cols].exterior

    if coord_type == 'x':
        # Get the x coordinates of the exterior
        return list(exterior.coords.xy[0])
    elif coord_type == 'y':
        # Get the y coordinates of the exterior
        return list(exterior.coords.xy[1])

def setup_plot(name=None, alpha=1):
    # import geospatial data in web mercator
    uk_polygons = convert_to_web_mercator(
            TVMsetup.get_country_natural_earth()[0])
    try:
        uk_parkrun_points = convert_to_web_mercator(
                import_shapefile("uk_parkruns"))
        uk_parkrun_areas = convert_to_web_mercator(
                import_shapefile("uk_parkrun_areas"))
    except:
        TVMsetup.setup()
        uk_parkrun_points = convert_to_web_mercator(
                import_shapefile("uk_parkruns"))
        uk_parkrun_areas = convert_to_web_mercator(
                import_shapefile("uk_parkrun_areas"))

    # create colour column
    uk_parkrun_areas["colour"] = 0
    uk_parkrun_points["colour"] = 0

    if name is not None:
        if type(name) == str:
            personal_runs_df = personal_parkrun.personal_parkrun_df(name)
        elif type(name) == list:
            personal_runs_df = personal_parkrun.group_parkrun(name)
        else:
            raise NameError(
                    "Unrecognised name type, must be single str or list")
        for index, row in uk_parkrun_areas.iterrows():
            if (uk_parkrun_areas.loc[index, "m2"] in
                    personal_runs_df["Event"].values):
                uk_parkrun_areas.loc[index, "colour"] = 1 * alpha

    # convert to points

    uk_polygons['x_uk'] = uk_polygons.apply(getPoly_xy, coord_type='x', axis=1)
    uk_polygons['y_uk'] = uk_polygons.apply(getPoly_xy, coord_type='y', axis=1)
    uk_map_sd = uk_polygons[["x_uk", "y_uk"]].copy()

    uk_parkrun_areas['x_p'] = uk_parkrun_areas.apply(
            getPoly_xy, coord_type='x', axis=1)
    uk_parkrun_areas['y_p'] = uk_parkrun_areas.apply(
            getPoly_xy, coord_type='y', axis=1)
    uk_parkrun_areas_sd = uk_parkrun_areas[["m2",
                                            "x_p",
                                            "y_p",
                                            "colour"]].copy()

    uk_parkrun_points["x"] = uk_parkrun_points.apply(
            getPoint_xy, coord="x", axis=1)
    uk_parkrun_points["y"] = uk_parkrun_points.apply(
            getPoint_xy, coord="y", axis=1)

    uk_parkrun_points_sd = uk_parkrun_points[["m2",
                                              "x",
                                              "y",
                                              "colour"]].copy()

    # convert to column data source
    uk_map_csd = ColumnDataSource(uk_map_sd)
    uk_parkrun_areas_cds = ColumnDataSource(uk_parkrun_areas_sd)
    uk_parkrun_points_cds = ColumnDataSource(uk_parkrun_points_sd)

    return (uk_map_csd, uk_parkrun_points_cds, uk_parkrun_areas_cds)


def simple_parkrun_areas_plot():
    """
    Simple plot of assicuated parkrun areas
    """
    (uk_map_csd, uk_parkrun_points, uk_parkrun_areas_cds) = setup_plot()

    tools = "pan, wheel_zoom, reset, hover, save"
    prun_map = bk.Figure(tools=tools, active_scroll="wheel_zoom",
                         x_axis_location=None, y_axis_location=None,
                         output_backend="webgl")
    prun_map.patches("x_uk", "y_uk", source=uk_map_csd,
                     line_color="black", line_width=1, fill_alpha=0.2,
                     fill_color="#b06600")
    areas = prun_map.patches("x_p", "y_p", source=uk_parkrun_areas_cds,
                             line_color="black", line_width=0.5,
                             fill_color="#8e8c13", fill_alpha="colour")

    hover = prun_map.select_one(HoverTool)
    hover.renderers = [areas]
    hover.point_policy = "follow_mouse"
    hover.tooltips = [("parkrun", "@m2")]

    bk.show(prun_map)
    filename = path.normpath("simple_area_map.html")
    filepath = path.join(map_output_folder, filename)
    bk.save(prun_map, filename=filepath,
            title=("UK parkruns"))
    return


def detailed_parkrun_areas_plot():
    """
    Detailed map of parkrun locations and associated areas
    """
    (uk_map_csd, uk_parkrun_points, uk_parkrun_areas_cds) = setup_plot()

    tools = "pan, wheel_zoom, reset, hover, save"
    prun_map = bk.Figure(tools=tools, active_scroll="wheel_zoom",
                         x_axis_location=None, y_axis_location=None,
                         output_backend="webgl")
    prun_map.patches("x_p", "y_p", source=uk_parkrun_areas_cds,
                     line_color="black", line_width=0.2,
                     fill_color="#8e8c13", fill_alpha=0.05)

#    prun_map.patches("x", "y", source=uk_map_csd,
#                     line_color="black", line_width=1, fill_alpha = 0.1)
    prun_map.circle(x="x", y="y", source=uk_parkrun_points, color='black',
                    size=1.5)

    prun_map.add_tile(uk)
    hover = prun_map.select_one(HoverTool)
    hover.point_policy = "follow_mouse"
    hover.tooltips = [("parkrun", "@m2")]

    bk.show(prun_map)
    filename = path.normpath("detailed_area_map.html")
    filepath = path.join(map_output_folder, filename)
    bk.save(prun_map, filename=filepath,
            title=("UK parkruns"))

    return


def personal_summary(name):
    if name is not None:
        if type(name) == str:
            personal_runs_df = personal_parkrun.personal_parkrun_df(name)
        elif type(name) == list:
            personal_runs_df = personal_parkrun.group_parkrun(name)
    uk_parkrun_areas = import_shapefile("uk_parkrun_areas")

    uk_parkrun_areas["completed"] = 0

    for index, row in uk_parkrun_areas.iterrows():
        if (uk_parkrun_areas.loc[index, "m2"] in
                personal_runs_df["Event"].values):
            uk_parkrun_areas.loc[index, "completed"] = 1

    uk_parkrun_areas["completed_area"] = (uk_parkrun_areas["area"]
                                          * uk_parkrun_areas["completed"])
    # group by region
    grouped = uk_parkrun_areas.groupby(["r"])
    # count number in each region
    total_by_region = grouped["m2"].agg(["count"])
    # sum completed in each region
    completed_by_region = grouped["completed"].agg(["sum"])

    personal_runs = personal_runs_df["Runs"].sum()

    p_index = 0
    while (personal_runs_df["Runs"] > p_index).sum() > p_index:
        p_index += 1

    total_uk_runs = len(uk_parkrun_areas.index)

    total_london_runs = total_by_region["count"][10]

    different_personal_runs = len(personal_runs_df["Event"])

    tourist_ratio = np.divide(different_personal_runs, personal_runs)

    personal_uk_runs = uk_parkrun_areas["completed"].sum()

    personal_london_runs = completed_by_region["sum"][10]

    percent_uk_runs = (personal_uk_runs / total_uk_runs)*100

    percent_uk_area = ((uk_parkrun_areas["completed_area"].sum()
                        / uk_parkrun_areas["area"].sum())
                        * 100)
    percent_london_runs = (personal_london_runs / total_london_runs)*100

    personal_runs_str = "Total runs: {:d}".format(personal_runs)
    different_runs_str = "Different runs: {:d}".format(different_personal_runs)
    p_index_str = "p-index: {:d}".format(p_index)
    tourist_ratio_str = "Tourist ratio: {:0.2f}".format(tourist_ratio)
    uk_runs_str = "Different UK runs: {:d} ({:0.2f} %)".format(
            personal_uk_runs, percent_uk_runs)
    percent_uk_area_str = "UK area covered: {:0.2f} %".format(percent_uk_area)
    london_runs_str = "Lon-done: {:d} ({:0.2f} %)".format(
            personal_london_runs, percent_london_runs)

    print(personal_runs_str)
    print(different_runs_str)
    print(p_index_str)
    print(tourist_ratio_str)
    print(uk_runs_str)
    print(percent_uk_area_str)
    print(london_runs_str)

    return (personal_runs_str, different_runs_str, p_index_str,
            tourist_ratio_str, uk_runs_str, percent_uk_area_str,
            london_runs_str)


def add_personal_details(plot, name):

    (personal_runs_str, different_runs_str, p_index_str, tourist_ratio_str,
     uk_runs_str, percent_uk_area_str,
     london_runs_str) = personal_summary(name)

    if type(name) == list:
        name = "Group"

    name_lab = Label(x=50, y=200, x_units='screen', y_units='screen',
                     text=name.title(), render_mode='canvas',
                     background_fill_color='white', background_fill_alpha=0.7)
    personal_runs_lab = Label(x=50, y=175, x_units='screen', y_units='screen',
                              text=personal_runs_str, render_mode='canvas',
                              background_fill_color='white',
                              background_fill_alpha=0.7)
    different_runs_lab = Label(x=50, y=150, x_units='screen', y_units='screen',
                               text=different_runs_str, render_mode='canvas',
                               background_fill_color='white',
                               background_fill_alpha=0.7)
    p_index_lab = Label(x=50, y=125, x_units='screen', y_units='screen',
                        text=p_index_str, render_mode='canvas',
                        background_fill_color='white',
                        background_fill_alpha=0.7)
    tourist_ratio_lab = Label(x=50, y=100, x_units='screen', y_units='screen',
                              text=tourist_ratio_str, render_mode='canvas',
                              background_fill_color='white',
                              background_fill_alpha=0.7)
    personal_UK_runs_lab = Label(x=50, y=75, x_units='screen',
                                 y_units='screen', text=uk_runs_str,
                                 render_mode='canvas',
                                 background_fill_color='white',
                                 background_fill_alpha=0.7)
    UK_area_lab = Label(x=50, y=50, x_units='screen', y_units='screen',
                        text=percent_uk_area_str, render_mode='canvas',
                        background_fill_color='white',
                        background_fill_alpha=0.7)
    London_runs_lab = Label(x=50, y=25, x_units='screen', y_units='screen',
                            text=london_runs_str, render_mode='canvas',
                            background_fill_color='white',
                            background_fill_alpha=0.7)

    plot.add_layout(name_lab)
    plot.add_layout(personal_runs_lab)
    plot.add_layout(different_runs_lab)
    plot.add_layout(p_index_lab)
    plot.add_layout(tourist_ratio_lab)
    plot.add_layout(personal_UK_runs_lab)
    plot.add_layout(UK_area_lab)
    plot.add_layout(London_runs_lab)


def simple_personal_plot(name="scot", details=True):
    """
    Simple plot of areas, coloured based on athletes completion.
    """
    (uk_map_csd, uk_parkrun_points, uk_parkrun_areas_cds) = setup_plot(name)

    tools = "pan, wheel_zoom, reset, hover, save"
    prun_map = bk.Figure(tools=tools, active_scroll="wheel_zoom",
                         x_axis_location=None, y_axis_location=None,
                         output_backend="webgl")
    prun_map.patches("x_uk", "y_uk", source=uk_map_csd,
                     line_color="black", line_width=1, fill_alpha=0.2,
                     fill_color="#b06600")
    areas = prun_map.patches("x_p", "y_p", source=uk_parkrun_areas_cds,
                             line_color="black", line_width=0.5,
                             fill_color="#8e8c13", fill_alpha="colour")

    hover = prun_map.select_one(HoverTool)
    hover.renderers = [areas]
    hover.point_policy = "follow_mouse"
    hover.tooltips = [("parkrun", "@m2")]

    if details:
        add_personal_details(prun_map, name)
    if type(name) == list:
        name = "Group"

    bk.show(prun_map)
    filename = path.normpath(name + "_simple_area_map.html")
    filepath = path.join(map_output_folder, filename)
    bk.save(prun_map, filename=filepath,
            title=(name+"'s UK parkruns"))

    return


def detailed_personal_plot(name="scot"):
    """
    Detailed map of parkrun locations and associated areas, coloured based on
    athletes completion
    """
    (uk_map_csd, uk_parkrun_points,
     uk_parkrun_areas_cds) = setup_plot(name, alpha=0.65)

    if type(name) == list:
        name = "Group"

    tools = "pan, wheel_zoom, reset, hover, save"
    prun_map = bk.Figure(tools=tools, active_scroll="wheel_zoom",
                         x_axis_location=None, y_axis_location=None,
                         output_backend="webgl")
    prun_map.patches("x_p", "y_p", source=uk_parkrun_areas_cds,
                     line_color="black", line_width=0.2,
                     fill_color="#8e8c13", fill_alpha="colour")

#    prun_map.patches("x", "y", source=uk_map_csd,
#                     line_color="black", line_width=1, fill_alpha = 0.1)
    prun_map.circle(x="x", y="y", source=uk_parkrun_points, color='black',
                    radius=150)  # size = 1.5

    prun_map.add_tile(uk)
    hover = prun_map.select_one(HoverTool)
    hover.point_policy = "follow_mouse"
    hover.tooltips = [("parkrun", "@m2")]

    bk.show(prun_map)
    filename = path.normpath(name + "_detailed_area_map.html")
    filepath = path.join(map_output_folder, filename)
    bk.save(prun_map, filename=filepath,
            title=(name+"'s UK parkruns"))
    return


if __name__ == "__main__":
    simple_personal_plot(name="scot")
    detailed_personal_plot(name="scot")
#    detailed_personal_plot(name=["scot","hayleigh","lewis", "sam"])
#    simple_personal_plot(name=["scot","hayleigh",
#                               "lewis", "sam"], details=True)

    pass