#!/usr/bin/env python
""" The script loads and extracts land cover area percentages over wilderness INON layers in Trøndelag.
 This script defines a workflow iterating over rindal kommune only, missing in previous workflows (inon_area_troendelag).
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
    output_directory = '/inon_outputs_rindal_official/'
    wilderness_outputs = working_directory + output_directory + 'wilderness_outputs/'
    wilderness_areas = working_directory + '/wilderness areas/'
    inon_ar50_clipped_inputs = working_directory + '/inon_ar50_clipped/'

    ar5_directory = os.fsencode(working_directory + '/clean_input_AR5_rindal/ar5_rindal/')

    if os.path.isdir(working_directory + output_directory):
        pass
    else:
        os.mkdir(working_directory + output_directory)


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

    inon_layers = {}
    inon_input_layers = {}
    year_areas = {}

    n50 = QgsVectorLayer(working_directory + '/Input_N50_layers/N50_AdministrativeOmråder.shp', 'n50_borders', 'ogr')
    forest_limit = QgsVectorLayer(working_directory + '/forest_limit/forest_limit_fixed.gpkg',
                                  'forest_limit', 'ogr')

    for file in os.listdir(wilderness_areas):
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
                                                    inon_input_layer.crs(), "GPKG", onlySelected=False)

            inon_layer = QgsVectorLayer(wilderness_outputs + 'inon_output_' + year + '.gpkg', 'inon_output_' + year,
                                        'ogr')
            project.addMapLayer(inon_layer)

            # Add new fields to inon_output attribute table
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
            n_provider.addAttributes([QgsField("forest_ar50_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("forest_ar50_area_perc", QVariant.Double)])
            n_provider.addAttributes([QgsField("myr_ar50_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("myr_ar50_area_perc", QVariant.Double)])
            n_provider.addAttributes([QgsField("mountain_ar50_area", QVariant.Double)])
            n_provider.addAttributes([QgsField("mountain_ar50_area_perc", QVariant.Double)])
            inon_layer.updateFields()
            inon_layer.commitChanges()

            inon_layers[year] = inon_layer
            inon_input_layers[year] = inon_input_layer
            #initialize the yearly dictionary containing lists of areas, per kommune
            year_areas[year] = defaultdict(list)


    for file in os.listdir(ar5_directory):
        filename = os.fsdecode(file)
        kommune_name = 'rindal'
        kommune_num = '1567'

        # extract the current kommune's contour polygon
        query = "Kommunenum = '" + kommune_num + "'"
        input_layer = n50
        kommune_border_name = 'n50_' + kommune_name
        print(query)
        print(kommune_border_name)
        n50_kommune = query_layer(query, input_layer, kommune_border_name)

        # now pointing to the layers with fixed geometries (clean_AR5_layers.geometries.py)
        ar5_kommune_full = QgsVectorLayer(
            working_directory + '/clean_input_AR5_layers/clean_ar5_' + kommune_num + '_' + kommune_name + '.gpkg',
            'ar5_clean_' + kommune_name, 'ogr')
        project.addMapLayer(ar5_kommune_full)

        for file in os.listdir(wilderness_areas):
            # In wilderness_areas folder the new inputs are inon_clean_year - which is the fixed-geometries inon layers.
            filename = os.fsdecode(file)

            if filename.endswith('.gpkg'):
                print(filename)
                year = filename[11:15]
                print(year)
                print(inon_layers)

                #inon_layer = inon_layers[year]
                inon_input_layer = inon_input_layers[year]
                print(inon_layers[year].featureCount())

                inon_layer_kommune_name = 'inon_kommune_' + kommune_name + '_' + year
                inon_layer_kommune = geoprocess_layer(clip_alg, inon_input_layer, n50_kommune,
                                                      inon_layer_kommune_name)

                ar50_troendelag_year = QgsVectorLayer(inon_ar50_clipped_inputs + 'inon_ar50_' + year + '.gpkg',
                                                      'inon_ar50_troendelag_' + year, 'ogr')

                ar50_kommune_name = 'ar50_inon_kommune_' + kommune_name + '_' + year
                ar50_kommune = geoprocess_layer(clip_alg, ar50_troendelag_year, n50_kommune,
                                                              ar50_kommune_name)


                # clip Ar5 layer over inon input
                ar5_kommune_name = 'ar5_inon_' + kommune_name + '_' + year
                ar5_kommune = geoprocess_layer(clip_alg, ar5_kommune_full, inon_layer_kommune,
                                                              ar5_kommune_name)

                # Filtering mountain areas from AR5, not yet clipped by forest limit
                query2 = u"ARTYPE = '50'"
                input_layer = ar5_kommune
                mountain_rough_name = 'ar5_mountain_rough_' + kommune_name + '_' + year
                ar5_mountain_rough_kommune = query_layer(query2, input_layer, mountain_rough_name)

                # clip mountain areas in AR5 by forest limit
                mountain_clean_name = 'ar5_mountain_clean_' + kommune_name + '_' + year
                ar5_mountain_clean_kommune = geoprocess_layer(clip_alg, ar5_mountain_rough_kommune, forest_limit,
                                                              mountain_clean_name)

                # Selecting forest type from AR5 (ARTYPE 30, which includes more detailed classes: ARSKOGBON)
                query3 = u"ARTYPE = '30'"
                input_layer = ar5_kommune
                forest_name = 'ar5_skog_' + kommune_name + '_' + year
                ar5_forest_kommune = query_layer(query3, input_layer, forest_name)

                # myr in ar5
                query4 = u"ARTYPE = '60'"
                input_layer = ar5_kommune
                myr_name = 'ar5_myr_' + kommune_name + '_' + year
                ar5_myr_kommune = query_layer(query4, input_layer, myr_name)

                # Semi-natural grassland AR5
                query5 = u"ARTYPE = '23'"
                input_layer = ar5_kommune
                grass_name = 'ar5_grass_' + kommune_name + '_' + year
                ar5_grass_kommune = query_layer(query5, input_layer, grass_name)

                # filter low-productive forest from forest layer (arskogbon = 11)
                query6 = u"ARSKOGBON = '11' or ARSKOGBON = '12'"
                input_layer = ar5_forest_kommune
                forest_11_name = 'ar5_skog_11_' + kommune_name + '_' + year
                ar5_forest_11_kommune = query_layer(query6, input_layer, forest_11_name)

                # Filter  Medium-productive forest from forest layer (Arskogbon = 13)
                query7 = u"ARSKOGBON = '13'"
                input_layer = ar5_forest_kommune
                forest_13_name = 'ar5_skog_13_' + kommune_name + '_' + year
                ar5_forest_13_kommune = query_layer(query7, input_layer, forest_13_name)

                # Filter  High-productive forest from forest layer (Arskogbon = 14)
                query8 = u"ARSKOGBON = '14' OR ARSKOGBON = '15'"
                input_layer = ar5_forest_kommune
                forest_14_name = 'ar5_skog_14_' + kommune_name + '_' + year
                ar5_forest_14_kommune = query_layer(query8, input_layer, forest_14_name)

                # Find non registered areas in AR5 current kommune
                query9 = u"ARTYPE = '99'"
                input_layer = ar5_kommune
                unregistered_name = 'ar5_unregistered_' + kommune_name + '_' + year
                ar5_unregistered_kommune = query_layer(query9, input_layer, unregistered_name)

                # clip AR50 kommune on unregistered AR5 areas
                ar50_coverunregistered_name = 'ar50_coverunregistered_' + kommune_name + '_' + year
                ar50_coverunregistered_kommune = geoprocess_layer(clip_alg, ar50_kommune, ar5_unregistered_kommune,
                                                                  ar50_coverunregistered_name)
                # find forest in clipped AR50 covering Ar5 unregistered areas
                query10 = u"ARTYPE = '30'"
                input_layer = ar50_coverunregistered_kommune
                ar50_forest_name = 'ar50_unregistered_forest_' + kommune_name + '_' + year
                ar50_unregistered_forest_kommune = query_layer(query10, input_layer, ar50_forest_name)

                # find myr in clipped AR50 covering Ar5 unregistered areas
                query11 = u"ARTYPE = '60'"
                input_layer = ar50_coverunregistered_kommune
                ar50_myr_name = 'ar50_unregistered_myr_' + kommune_name + '_' + year
                ar50_unregistered_myr_kommune = query_layer(query11, input_layer, ar50_myr_name)

                # find mountain in clipped AR50 covering Ar5 unregistered areas
                query11 = u"ARTYPE = '50'"
                input_layer = ar50_coverunregistered_kommune
                ar50_mountain_rough_name = 'ar50_unregistered_mountain_rough_' + kommune_name + '_' + year
                ar50_unregistered_mountain_rough_kommune = query_layer(query11, input_layer, ar50_mountain_rough_name)

                # clip mountain areas in AR50 by forest limit
                ar50_mountain_clean_name = 'ar50_mountain_clean_' + kommune_name + '_' + year
                ar50_unregistered_mountain_clean_kommune = geoprocess_layer(clip_alg,
                                                                            ar50_unregistered_mountain_rough_kommune,
                                                                            forest_limit,
                                                                            ar50_mountain_clean_name)

                ####################################################
                # Calculate area and area percentage on inon layer #
                ####################################################



                total_area = calculate_area_over_clip(inon_layer_kommune)
                year_areas[year]['total_area'].append(total_area if total_area else 0)
                print(total_area)
                if total_area > 0:

                    myr_area = calculate_area_over_clip(ar5_myr_kommune)
                    year_areas[year]['myr_area'].append(myr_area if myr_area else 0)

                    grass_area = calculate_area_over_clip(ar5_grass_kommune)
                    year_areas[year]['grass_area'].append(grass_area)

                    mountain_area = calculate_area_over_clip(ar5_mountain_clean_kommune)
                    year_areas[year]['mountain_area'].append(mountain_area)

                    forest_11_area = calculate_area_over_clip(ar5_forest_11_kommune)
                    year_areas[year]['forest_11_area'].append(forest_11_area)

                    forest_13_area = calculate_area_over_clip(ar5_forest_13_kommune)
                    year_areas[year]['forest_13_area'].append(forest_13_area)

                    forest_14_area = calculate_area_over_clip(ar5_forest_14_kommune)
                    year_areas[year]['forest_14_area'].append(forest_14_area)

                    forest_ar50_area = calculate_area_over_clip(ar50_unregistered_forest_kommune)
                    year_areas[year]['forest_ar50_area'].append(forest_ar50_area)

                    myr_ar50_area = calculate_area_over_clip(ar50_unregistered_myr_kommune)
                    year_areas[year]['myr_ar50_area'].append(myr_ar50_area)

                    mountain_ar50_area = calculate_area_over_clip(ar50_unregistered_mountain_clean_kommune)
                    year_areas[year]['mountain_ar50_area'].append(mountain_ar50_area)


    print(year_areas)
    import pickle
    with open(wilderness_outputs + 'year_areas.pickle', 'wb') as f:
        # Pickle the 'data' dictionary using the highest protocol available.
        pickle.dump(year_areas, f, pickle.HIGHEST_PROTOCOL)

    # In this case key is the year, value is the inon output layer where areas are stored
    for key, value in inon_layers.items():
        with edit(value):
            for i, feat in enumerate(value.getFeatures()):
                total_area = sum(year_areas[key]['total_area'])
                myr_area = sum(year_areas[key]['myr_area'])
                grass_area = sum(year_areas[key]['grass_area'])
                mountain_area = sum(year_areas[key]['mountain_area'])
                forest_11_area = sum(year_areas[key]['forest_11_area'])
                forest_13_area = sum(year_areas[key]['forest_13_area'])
                forest_14_area = sum(year_areas[key]['forest_14_area'])
                forest_ar50_area = sum(year_areas[key]['forest_ar50_area'])
                myr_ar50_area = sum(year_areas[key]['myr_ar50_area'])
                mountain_ar50_area = sum(year_areas[key]['mountain_ar50_area'])

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



















