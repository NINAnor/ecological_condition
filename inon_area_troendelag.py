#!/usr/bin/env python
""" The script loads and extracts land cover area percentages over wilderness INON layers in Trøndelag.
 This script defines a workflow iterating over all the Kommunes in Trøndelag Fylke.
 The script is designed to work with the 'Script runner' plugin in QGIS 3.0 """

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
import processing
from processing.core.Processing import Processing
import os
from collections import defaultdict

Processing.initialize()

def run_script(iface):

    # Set the encoding
    QgsSettings().setValue('/Processing/encoding', 'utf-8')

    # Set the working environment folders. Requires input data being organized in a precise structure
    working_directory = "C:/Data/Simon"
    output_directory = '/inon_outputs_new/'
    wilderness_outputs = working_directory + output_directory + 'wilderness_outputs/'
    wilderness_areas = working_directory + '/wilderness areas/'

    ar5_directory = os.fsencode(working_directory + '/Input_AR5_layers_all/')


    if os.path.isdir(wilderness_outputs):
        pass
    else:
        os.mkdir(wilderness_outputs)

    #Greet Simon!
    print("Hello Simon! Starting the processing now!")
    project = QgsProject.instance()

    # Remove any layer previously existing in current project
    project.removeAllMapLayers()

    # Remove also all groups, if any
    root = project.layerTreeRoot()
    root.removeAllChildren()

    # Now loading the geometry clean version of AR50 troendelag layer
    ar50_troendelag = QgsVectorLayer(working_directory + '/Input_AR50_layers/clean_ar50_troendelag.gpkg',
                                     'ar50_troendelag', 'ogr')
    project.addMapLayer(ar50_troendelag)

    clip_alg = 'qgis:clip'

    def query_layer(query, input_layer, output_name):
        selection = input_layer.getFeatures(QgsFeatureRequest().setFilterExpression(query))
        input_layer.select([k.id() for k in selection])
        QgsVectorFileWriter.writeAsVectorFormat(input_layer,
                                                working_directory + output_directory + output_name,
                                                "utf-8", input_layer.crs(), "GPKG", onlySelected=True)
        layer = QgsVectorLayer(working_directory + output_directory + output_name + '.gpkg', output_name, 'ogr')
        # project.addMapLayer(layer)
        input_layer.removeSelection()
        return layer

    def geoprocess_layer(alg, input_layer, overlay, output_name, add_layer=False):
        params = {"INPUT": input_layer, "OVERLAY": overlay,
                  "OUTPUT": working_directory + output_directory + output_name + '.gpkg'}
        processing.run(alg, params)
        output_layer = QgsVectorLayer(working_directory + output_directory + output_name + '.gpkg',
                                      output_name, 'ogr')
        if add_layer == True:
            project.addMapLayer(output_layer)
        return output_layer

    def calculate_area_over_clip(input_layer):
        area = 0
        with edit(input_layer):
            for featc in input_layer.getFeatures():
                calculator = QgsDistanceArea()

                # calculator.setEllipsoid('WGS84')
                # calculator.setEllipsoidalMode(True)

                geom = featc.geometry()

                # if only simple polygon, calculate only for this
                if geom.isMultipart() is False:
                    polyg = geom.asPolygon()
                    if len(polyg) > 0:
                        area = area + calculator.measurePolygon(polyg[0])

                # is Multipart
                else:
                    multi = geom.asMultiPolygon()
                    for polyg in multi:
                        area = area + calculator.measurePolygon(polyg[0])

        return area

    for file in os.listdir(wilderness_areas):
        #In wilderness_areas folder the new inputs are inon_clean_year - which is the fixed-geometries inon layers.
        filename = os.fsdecode(file)

        if filename.endswith('.gpkg'):
            print(filename)
            year = filename[11:15]
            print(year)

            inon_input_layer = QgsVectorLayer(wilderness_areas + filename, 'inon_input_' + year, 'ogr')
            project.addMapLayer(inon_input_layer)

            QgsVectorFileWriter.writeAsVectorFormat(inon_input_layer,
                                                    wilderness_outputs + 'inon_output_' + year,
                                                    "utf-8",
                                                    inon_input_layer.crs(), "GPKG", onlySelected=True)

            inon_layer = QgsVectorLayer(wilderness_outputs + 'inon_output_' + year, 'inon_output_' + year, 'ogr')
            project.addMapLayer(inon_layer)

            ar50_troendelag_year = QgsVectorLayer(output_directory + 'inon_ar50_' + year + '.gpkg',
                                             'inon_ar50_troendelag_' + year, 'ogr')

            for file in os.listdir(ar5_directory):
                filename = os.fsdecode(file)
                kommune_name = filename[15:-19]
                if kommune_name == 'Rindal':
                    kommune_num = '1567'
                else:
                    kommune_num = filename[10:].split('_', 1)[0]

                # extract the current kommune's contour polygon
                query = "Kommunenum = '" + kommune_num + "'"
                input_layer = n50
                kommune_border_name = 'n50_' + kommune_name
                print(query)
                print(kommune_border_name)
                n50_kommune = query_layer(query, input_layer, kommune_border_name)



















            query1 = u"ARTYPE = '30'"
            input_layer = ar50_troendelag_year
            forest_name = 'ar50_skog_' + year
            ar50_forest_year = query_layer(query1, input_layer, forest_name)

            query2 = u"ARTYPE = '60'"
            input_layer = ar50_troendelag_year
            myr_name = 'ar50_myr_' + year
            ar50_myr_year = query_layer(query2, input_layer, myr_name)

            query3 = u"ARTYPE = '23'"
            input_layer = ar50_troendelag_year
            grass_name = 'ar50_grass_' + year
            ar50_grass_year = query_layer(query3, input_layer, grass_name)

            query4 = u"ARTYPE = '50'"
            input_layer = ar50_troendelag_year
            mountain_name = 'ar50_mountain_' + year
            ar50_mountain_year = query_layer(query4, input_layer, mountain_name)

            query5 = u"ARSKOGBON = '11' or ARSKOGBON = '12'"
            input_layer = ar50_forest_year
            forest_11_name = 'ar50_forest_11_' + year
            ar50_forest_11_year = query_layer(query5, input_layer, forest_11_name)

            query6 = u"ARSKOGBON = '13"
            input_layer = ar50_forest_year
            forest_13_name = 'ar50_forest_13_' + year
            ar50_forest_13_year = query_layer(query6, input_layer, forest_13_name)

            query7 = u"ARSKOGBON = '14' or ARSKOGBON = '15'"
            input_layer = ar50_forest_year
            forest_14_name = 'ar50_forest_14_' + year
            ar50_forest_14_year = query_layer(query7, input_layer, forest_14_name)

            #############################################################################
            # Calculate areas of land cover classes on INON troendelag layer (per year) #
            #############################################################################

            # Add new fields to nitrogen_kommune attribute table
            '''
            n_provider = inon_layer.dataProvider()
            n_provider.addAttributes([QgsField("total_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("myr_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("myr_area_perc", QVariant.Double)])
            n_provider.addAttributes([QgsField("grass_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("grass_area_perc", QVariant.Double)])
            n_provider.addAttributes([QgsField("mountain_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("mountain_area_perc", QVariant.Double)])
            n_provider.addAttributes([QgsField("forest_11_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("forest_11_area_perc", QVariant.Double)])
            n_provider.addAttributes([QgsField("forest_13_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("forest_13_area_perc", QVariant.Double)])
            n_provider.addAttributes([QgsField("forest_14_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("forest_14_area_perc", QVariant.Double)])
            inon_layer.updateFields()
            '''


            total_areas = {}
            myr_areas = {}
            grass_areas = {}
            mountain_areas = {}
            forest_11_areas = {}
            forest_13_areas = {}
            forest_14_areas = {}

            total_area = calculate_area_over_clip(inon_layer)

            #total_areas[i] = myr_area

            myr_area = calculate_area_over_clip(ar50_myr_year)
            print(myr_area)
            #myr_areas[i] = myr_area

            grass_area = calculate_area_over_clip(ar50_grass_year)
            #grass_areas[i] = grass_area

            mountain_area = calculate_area_over_clip(ar50_mountain_year)
            #mountain_areas[i] = mountain_area

            forest_11_area = calculate_area_over_clip(ar50_forest_11_year)
            #forest_11_areas[i] = forest_11_area

            forest_13_area = calculate_area_over_clip(ar50_forest_13_year)
            #forest_13_areas[i] = forest_13_area

            forest_14_area = calculate_area_over_clip(ar50_forest_14_year)
            #forest_14_areas[i] = forest_14_area

            myr_perc = myr_area / total_area * 100
            grass_perc = grass_area / total_area * 100
            mountain_perc = mountain_area / total_area * 100
            forest_11_perc = forest_11_area / total_area * 100
            forest_13_perc = forest_13_area / total_area * 100
            forest_14_perc = forest_14_area / total_area * 100

            with edit(inon_layer):
                for i, feat in enumerate(inon_layer.getFeatures()):
                    feat.setAttribute('total_area', total_area)
                    feat.setAttribute('myr_area', myr_area)
                    feat.setAttribute('grass_area', grass_area)
                    feat.setAttribute('mountain_area', mountain_area)
                    feat.setAttribute('forest_11_area', forest_11_area)
                    feat.setAttribute('forest_13_area', forest_13_area)
                    feat.setAttribute('forest_14_area', forest_14_area)

                    feat.setAttribute('myr_area_perc', myr_perc)
                    feat.setAttribute('grass_area_perc', grass_perc)
                    feat.setAttribute('mountain_area_perc', mountain_perc)
                    feat.setAttribute('forest_11_area_perc', forest_11_perc)
                    feat.setAttribute('forest_13_area_perc', forest_13_perc)
                    feat.setAttribute('forest_14_area_perc', forest_14_perc)
                    inon_layer.updateFeature(feat)

















