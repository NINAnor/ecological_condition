#!/usr/bin/env python
""" The script unpickles and write inon areas results from inon_area_troendelag.py.
 The script is designed to work with the 'Script runner' plugin in QGIS 3.0 """

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
import processing
from processing.core.Processing import Processing
import os
from collections import defaultdict
import pickle

Processing.initialize()

def run_script(iface):

    # Set the encoding
    QgsSettings().setValue('/Processing/encoding', 'utf-8')

    # Set the working environment folders. Requires input data being organized in a precise structure
    working_directory = "C:/Data/Simon"
    output_directory = '/inon_outputs_official/'
    wilderness_outputs = working_directory + output_directory + 'wilderness_outputs/'

    project = QgsProject.instance()

    # Remove any layer previously existing in current project
    project.removeAllMapLayers()

    # Remove also all groups, if any
    root = project.layerTreeRoot()
    root.removeAllChildren()

    with open(wilderness_outputs + 'year_areas.pickle', 'rb') as unpickled:
        year_areas = pickle.load(unpickled)

    #year_areas = pickle.load(wilderness_outputs + 'year_areas.pickle', 'rb')

    for file in os.listdir(wilderness_outputs):
        filename = os.fsdecode(file)

        if filename.endswith('.gpkg'):
            print(filename)
            year = filename[12:16]
            print(year)

            value = QgsVectorLayer(wilderness_outputs + 'inon_output_' + year + '.gpkg', 'inon_output_' + year,
                                    'ogr')


            with edit(value):
                for i, feat in enumerate(value.getFeatures()):
                    total_area = sum(year_areas[year]['total_area'])
                    myr_area = sum(year_areas[year]['myr_area'])
                    grass_area = sum(year_areas[year]['grass_area'])
                    mountain_area = sum(year_areas[year]['mountain_area'])
                    forest_11_area = sum(year_areas[year]['forest_11_area'])
                    forest_13_area = sum(year_areas[year]['forest_13_area'])
                    forest_14_area = sum(year_areas[year]['forest_14_area'])
                    forest_ar50_area = sum(year_areas[year]['forest_ar50_area'])
                    myr_ar50_area = sum(year_areas[year]['myr_ar50_area'])
                    mountain_ar50_area = sum(year_areas[year]['mountain_ar50_area'])

                    myr_perc = myr_area / total_area * 100
                    grass_perc = grass_area / total_area * 100
                    mountain_perc = mountain_area / total_area * 100
                    forest_11_perc = forest_11_area / total_area * 100
                    forest_13_perc = forest_13_area / total_area * 100
                    forest_14_perc = forest_14_area / total_area * 100
                    forest_ar50_perc = forest_ar50_area / total_area * 100
                    myr_ar50_perc = myr_ar50_area / total_area * 100
                    mountain_ar50_perc = mountain_ar50_area / total_area * 100

                    feat.setAttribute('total_area', total_area)
                    feat.setAttribute('myr_area', myr_area)
                    feat.setAttribute('grass_area', grass_area)
                    feat.setAttribute('mountain_area', mountain_area)
                    feat.setAttribute('forest_11_area', forest_11_area)
                    feat.setAttribute('forest_13_area', forest_13_area)
                    feat.setAttribute('forest_14_area', forest_14_area)
                    feat.setAttribute('forest_ar50_area', forest_ar50_area)
                    feat.setAttribute('myr_ar50_area', myr_ar50_area)
                    feat.setAttribute('mountain_ar50_area', mountain_ar50_area)

                    feat.setAttribute('myr_area_perc', myr_perc)
                    feat.setAttribute('grass_area_perc', grass_perc)
                    feat.setAttribute('mountain_area_perc', mountain_perc)
                    feat.setAttribute('forest_11_area_perc', forest_11_perc)
                    feat.setAttribute('forest_13_area_perc', forest_13_perc)
                    feat.setAttribute('forest_14_area_perc', forest_14_perc)
                    feat.setAttribute('forest_ar50_area_perc', forest_ar50_perc)
                    feat.setAttribute('myr_ar50_area_perc', myr_ar50_perc)
                    feat.setAttribute('mountain_ar50_area_perc', mountain_ar50_perc)
                    value.updateFeature(feat)