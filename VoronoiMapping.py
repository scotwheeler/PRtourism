# -*- coding: utf-8 -*-
"""
Voronoi mapping
Created on Fri Sep 15 11:45:13 2017

@author: Scot Wheeler
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi
from shapely.geometry import Polygon
import geopandas as gpd
from fiona.crs import from_epsg

__version__ = 2.0


def voronoi_polygons(points_df, overall_map):
    """
    Creates a voronoi map of the points, to fill entirety of overall_map
    Polygons need cropping seperately.
    Input
    -----
    points_df : geodataframe
        Geodataframe of points only

    overall_map
        Geodataframe of polygons forming a country only

    """
    bbox = overall_map["geometry"][0].bounds
    # use hypotenuse to ensure distance to infinite points is outside uk.
    max_bound = np.sqrt((bbox[2]-bbox[0])**2 + (bbox[3]-bbox[1])**2)
    # make copy of points
    points = points_df[["lo", "la"]].copy()
    # generate voronoi object
    vor = Voronoi(points)
    # create voronoi polygons as geodataframe
    polygons = voronoi_finite_polygons_2d(vor, radius=max_bound)
    return polygons


def voronoi_finite_polygons_2d(vor, radius=None):
    """
    Reconstruct infinite voronoi regions in a 2D diagram to finite
    regions.

    Parameters
    ----------
    vor : Voronoi
        Input diagram
    radius : float, optional
        Distance to 'points at infinity'.

    Returns
    -------
    polygons : a geodataframe of voronoi polygons
    regions : list of tuples
        Indices of vertices in each revised Voronoi regions.
    vertices : list of tuples
        Coordinates for revised Voronoi vertices. Same as coordinates
        of input vertices, with 'points at infinity' appended to the
        end.

    """

    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")

    new_regions = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = vor.points.ptp().max()

    # Construct a map containing all ridges for a given point
    all_ridges = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    # Reconstruct infinite regions
    for p1, region in enumerate(vor.point_region):
        vertices = vor.regions[region]

        if all(v >= 0 for v in vertices):
            # finite region
            new_regions.append(vertices)
            continue

        # reconstruct a non-finite region
        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                # finite ridge: already in the region
                continue

            # Compute the missing endpoint of an infinite ridge

            t = vor.points[p2] - vor.points[p1] # tangent
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])  # normal

            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius

            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        # sort region counterclockwise
        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)]

        # finish
        new_regions.append(new_region.tolist())

    regions = new_regions

    vertices = np.asarray(new_vertices)
    polys = []
    for region in regions:
        polygon = vertices[region]
        poly = Polygon(polygon)
        polys.append(poly)

    # create geodataframe
    polygons = gpd.GeoDataFrame({"geometry": polys})
    polygons.crs = from_epsg(4326)  # change to WGS84 (decimal degrees)

    return polygons
