#!/usr/bin/env python
""" The script loads and extracts land cover area percentages over a nitrogen layer in Trøndelag.
 This script defines a workflow iterating over the Rindal kommune only, missing in previous workflows (nitrogen_lc_area_workflow_troendelag).
 The script is designed to work with the 'Script runner' plugin in QGIS 3.0 """

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
import processing
from processing.core.Processing import Processing
import os
from collections import defaultdict
from multiprocessing import Pool, TimeoutError
import time

Processing.initialize()

def run_script(iface):

    # Set the encoding
    QgsSettings().setValue('/Processing/encoding', 'utf-8')

    # Set the working environment folders. Requires input data being organized in a precise structure
    working_directory = "C:/Data/Simon"
    rindal_input = working_directory + '/clean_input_AR5_rindal'
    rindal_output = working_directory + '/rindal_outputs_official/'
    output_directory = rindal_output + 'outputs/'

    if os.path.isdir(rindal_output):
        pass
    else:
        os.mkdir(rindal_output)

    if os.path.isdir(output_directory):
        pass
    else:
        os.mkdir(output_directory)


    #Greet Simon!
    print("Hello Simon! Starting the processing now!")
    project = QgsProject.instance()

    # Remove any layer previously existing in current project
    project.removeAllMapLayers()

    # Remove also all groups, if any
    root = project.layerTreeRoot()
    root.removeAllChildren()

    rindal_polygon = QgsVectorLayer(rindal_input + '/rindal_polygon.gpkg', 'n50_borders', 'ogr')
    # Now loading the geometry clean version of AR50 troendelag layer
    ar50_troendelag = QgsVectorLayer(working_directory + '/Input_AR50_layers/clean_ar50_troendelag.gpkg', 'ar50_troendelag', 'ogr')
    #ar50_troendelag = QgsVectorLayer(working_directory + '/Input_AR50_layers/AR50_50_5e8c55.shp', 'ar50_troendelag', 'ogr')
    input_nitrogen = QgsVectorLayer(rindal_input + '/nitrogen_rindal_clip_fixed.gpkg', 'input_nitrogen', 'ogr')

    alg = u'native:fixgeometries'
    params = {"INPUT": input_nitrogen,
              "OUTPUT": rindal_output + 'nitrogen_rindal_output.gpkg'}
    processing.run(alg, params)

    # Save the nitrogen layer as an output with a different name

    nitrogen = QgsVectorLayer(rindal_output + 'nitrogen_rindal_output.gpkg', 'nitrogen', 'ogr')
    forest_limit_rough = QgsVectorLayer(rindal_input + '/extra_forest_clipped_shape_10.shp',
                                  'forest_limit_rough', 'ogr')

    alg = u'native:fixgeometries'
    params = {"INPUT": forest_limit_rough,
              "OUTPUT": rindal_output + 'forest_limit_rindal.gpkg'}
    processing.run(alg, params)

    forest_limit = QgsVectorLayer(rindal_output + 'forest_limit_rindal.gpkg',
                                        'forest_limit', 'ogr')

    project.addMapLayer(rindal_polygon)
    project.addMapLayer(ar50_troendelag)
    project.addMapLayer(nitrogen)
    project.addMapLayer(forest_limit)

    def query_layer(query, input_layer, output_name):
        selection = input_layer.getFeatures(QgsFeatureRequest().setFilterExpression(query))
        input_layer.select([k.id() for k in selection])
        QgsVectorFileWriter.writeAsVectorFormat(input_layer,
                                                output_directory + output_name,
                                                "utf-8", input_layer.crs(), "GPKG", onlySelected=True)
        layer = QgsVectorLayer(output_directory + output_name+'.gpkg', output_name, 'ogr')
        #project.addMapLayer(layer)
        input_layer.removeSelection()
        return layer

    clip_alg = 'qgis:clip'

    def geoprocess_layer(alg, input_layer, overlay, output_name, add_layer=False):
        params = {"INPUT": input_layer, "OVERLAY": overlay,
              "OUTPUT": output_directory + output_name + '.gpkg'}
        processing.run(alg, params)
        output_layer = QgsVectorLayer(output_directory + output_name + '.gpkg',
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

    # This will be a dictionary having as a key the lnr identification number of each rectangle fragment,
    # and as a value a list of dictionaries. Each dictionary in list will contain the area values of a rectangle
    # fragment with the same id of the original whole rectangle.
    rect_frag_area_dict = defaultdict(list)

    ar5_directory = os.fsencode(rindal_input + '/ar5_rindal/')

    kommune_name = 'rindal'
    kommune_num = '1567'

    nitrogen_kommune = nitrogen

    #n50_kommune = rindal_polygon

    # clip ar50 over current Kommune
    ar50_kommune_name = 'ar50_' + kommune_name
    ar50_kommune = QgsVectorLayer(rindal_input + ar50_kommune_name + '.gpkg',
                                            ar50_kommune_name, 'ogr')

    # now pointing to the layers with fixed geometries (clean_AR5_layers_geometries.py)
    ar5_kommune = QgsVectorLayer(
        rindal_input + '/ar5_rindal/clean_ar5_' + kommune_num + '_' + kommune_name + '.gpkg',
        'ar5_clean_' + kommune_name, 'ogr')
    project.addMapLayer(ar5_kommune)

    # Filtering mountain areas from AR5, not yet clipped by forest limit
    query2 = u"ARTYPE = '50'"
    input_layer = ar5_kommune
    mountain_rough_name = 'ar5_mountain_rough_' + kommune_name
    print(query2)
    print(mountain_rough_name)
    ar5_mountain_rough_kommune = query_layer(query2, input_layer, mountain_rough_name)

    # clip mountain areas in AR5 by forest limit
    mountain_clean_name = 'ar5_mountain_clean_' + kommune_name
    ar5_mountain_clean_kommune = geoprocess_layer(clip_alg, ar5_mountain_rough_kommune, forest_limit, mountain_clean_name)

    # Selecting forest type from AR5 (ARTYPE 30, which includes more detailed classes: ARSKOGBON)
    query3 = u"ARTYPE = '30'"
    input_layer = ar5_kommune
    forest_name = 'ar5_skog_' + kommune_name
    ar5_forest_kommune = query_layer(query3, input_layer, forest_name)

    # myr in ar5
    query4 = u"ARTYPE = '60'"
    input_layer = ar5_kommune
    myr_name = 'ar5_myr_' + kommune_name
    ar5_myr_kommune = query_layer(query4, input_layer, myr_name)

    # Semi-natural grassland AR5
    query5 = u"ARTYPE = '23'"
    input_layer = ar5_kommune
    grass_name = 'ar5_grass_' + kommune_name
    ar5_grass_kommune = query_layer(query5, input_layer, grass_name)

    # filter low-productive forest from forest layer (arskogbon = 11)
    query6 = u"ARSKOGBON = '11' or ARSKOGBON = '12'"
    input_layer = ar5_forest_kommune
    forest_11_name = 'ar5_skog_11_' + kommune_name
    ar5_forest_11_kommune = query_layer(query6, input_layer, forest_11_name)

    # Filter  Medium-productive forest from forest layer (Arskogbon = 13)
    query7 = u"ARSKOGBON = '13'"
    input_layer = ar5_forest_kommune
    forest_13_name = 'ar5_skog_13_' + kommune_name
    ar5_forest_13_kommune = query_layer(query7, input_layer, forest_13_name)

    # Filter  High-productive forest from forest layer (Arskogbon = 14)
    query8 = u"ARSKOGBON = '14' OR ARSKOGBON = '15'"
    input_layer = ar5_forest_kommune
    forest_14_name = 'ar5_skog_14_' + kommune_name
    ar5_forest_14_kommune = query_layer(query8, input_layer, forest_14_name)

    # Find non registered areas in AR5 current kommune
    query9 = u"ARTYPE = '99'"
    input_layer = ar5_kommune
    unregistered_name = 'ar5_unregistered_' + kommune_name
    ar5_unregistered_kommune = query_layer(query9, input_layer, unregistered_name)

    # clip AR50 kommune on unregistered AR5 areas
    ar50_coverunregistered_name = 'ar5_coverunregistered_' + kommune_name
    ar50_coverunregistered_kommune = geoprocess_layer(clip_alg, ar50_kommune, ar5_unregistered_kommune,
                                                      ar50_coverunregistered_name)
    # find forest in clipped AR50 covering Ar5 unregistered areas
    query10 = u"ARTYPE = '30'"
    input_layer = ar50_coverunregistered_kommune
    ar50_forest_name = 'ar50_unregistered_forest_' + kommune_name
    ar50_unregistered_forest_kommune = query_layer(query10, input_layer, ar50_forest_name)

    # find myr in clipped AR50 covering Ar5 unregistered areas
    query11 = u"ARTYPE = '60'"
    input_layer = ar50_coverunregistered_kommune
    ar50_myr_name = 'ar50_unregistered_myr_' + kommune_name
    ar50_unregistered_myr_kommune = query_layer(query11, input_layer, ar50_myr_name)

    # find mountain in clipped AR50 covering Ar5 unregistered areas
    query11 = u"ARTYPE = '50'"
    input_layer = ar50_coverunregistered_kommune
    ar50_mountain_rough_name = 'ar50_unregistered_mountain_rough_' + kommune_name
    ar50_unregistered_mountain_rough_kommune = query_layer(query11, input_layer, ar50_mountain_rough_name)

    # clip mountain areas in AR50 by forest limit
    ar50_mountain_clean_name = 'ar50_mountain_clean_' + kommune_name
    ar50_unregistered_mountain_clean_kommune = geoprocess_layer(clip_alg, ar50_unregistered_mountain_rough_kommune,
                                                                forest_limit,
                                                                ar50_mountain_clean_name)

    ######################################################################
    # Calculate area percentage per nitrogen rectangular clipped polygon #
    ######################################################################

    # Add new fields to nitrogen_kommune attribute table
    n_provider = nitrogen_kommune.dataProvider()
    n_provider.addAttributes([QgsField("area_rect", QVariant.Double)])
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
    nitrogen_kommune.updateFields()

    rect_areas = {}
    myr_areas = {}
    grass_areas = {}
    mountain_areas = {}
    forest_11_areas = {}
    forest_13_areas = {}
    forest_14_areas = {}
    forest_ar50_areas = {}
    myr_ar50_areas = {}
    mountain_ar50_areas = {}

    feats_nit = [feat for feat in nitrogen_kommune.getFeatures()]

    #########################################################
    # iterating over rectangular polygons of nitrogen layer #
    #########################################################

    for i, feat in enumerate(feats_nit):
        area_rect = 0
        calculator = QgsDistanceArea()
        geom1 = feat.geometry()
        if geom1.isMultipart() is False:
            pol = geom1.asPolygon()
            if len(pol) > 0:
                area_rect = calculator.measurePolygon(pol[0])
        else:  # is Multipart
            multi = geom1.asMultiPolygon()
            for polyg in multi:
                area_rect = area_rect + calculator.measurePolygon(polyg[0])
        rect_areas[i] = area_rect

        # selecting each rectangular nitrogen polygon one by one
        nitrogen_kommune.select(feat.id())
        temp_feat_layer = nitrogen_kommune.materialize(
            QgsFeatureRequest().setFilterFids(nitrogen_kommune.selectedFeatureIds()))
        # project.addMapLayer(temp_feat_layer)

        # process grassland
        ar5_grass_kommune_clip_name = 'ar5_grass_clip_' + kommune_name + '_' + str(i)
        temp_grass_clip = geoprocess_layer(clip_alg, ar5_grass_kommune, temp_feat_layer, ar5_grass_kommune_clip_name,
                                           add_layer=False)

        # process Myr
        ar5_myr_kommune_clip_name = 'ar5_myr_clip_' + kommune_name + '_' + str(i)
        temp_myr_clip = geoprocess_layer(clip_alg, ar5_myr_kommune, temp_feat_layer, ar5_myr_kommune_clip_name,
                                         add_layer=False)

        # process mountain
        ar5_mountain_kommune_clip_name = 'ar5_mountain_clip_' + kommune_name + '_' + str(i)
        temp_mountain_clip = geoprocess_layer(clip_alg, ar5_mountain_clean_kommune, temp_feat_layer,
                                              ar5_mountain_kommune_clip_name, add_layer=False)

        ###########################
        #  forest sub-classes ###
        ###########################

        # process skog with ARskogbon = 11 and 12
        ar5_forest_11_kommune_name = 'ar5_forest_11_kommune_' + kommune_name + '_' + str(i)
        temp_forest_11 = geoprocess_layer(clip_alg, ar5_forest_11_kommune, temp_feat_layer, ar5_forest_11_kommune_name,
                                          add_layer=False)

        # process skog with ARskogbon = 13
        ar5_forest_13_kommune_name = 'ar5_forest_13_kommune_' + kommune_name + '_' + str(i)
        temp_forest_13 = geoprocess_layer(clip_alg, ar5_forest_13_kommune, temp_feat_layer, ar5_forest_13_kommune_name,
                                          add_layer=False)

        # process skog with ARskogbon = 14 and 15
        ar5_forest_14_kommune_name = 'ar5_forest_14_kommune_' + kommune_name + '_' + str(i)
        temp_forest_14 = geoprocess_layer(clip_alg, ar5_forest_14_kommune, temp_feat_layer, ar5_forest_14_kommune_name,
                                          add_layer=False)

        ar50_unregistered_forest_kommune_name = 'ar50_unregistered_forest_kommune_' + kommune_name + '_' + str(i)
        temp_forest_ar50 = geoprocess_layer(clip_alg, ar50_unregistered_forest_kommune, temp_feat_layer,
                                            ar50_unregistered_forest_kommune_name, add_layer=False)

        ar50_unregistered_myr_kommune_name = 'ar50_unregistered_myr_kommune_' + kommune_name + '_' + str(i)
        temp_myr_ar50 = geoprocess_layer(clip_alg, ar50_unregistered_myr_kommune, temp_feat_layer,
                                         ar50_unregistered_myr_kommune_name, add_layer=False)

        ar50_unregistered_mountain_kommune_name = 'ar50_unregistered_mountain_kommune_' + kommune_name + '_' + str(i)
        temp_mountain_ar50 = geoprocess_layer(clip_alg, ar50_unregistered_mountain_clean_kommune, temp_feat_layer,
                                              ar50_unregistered_mountain_kommune_name, add_layer=False)

        ############################################
        # Store areas per fragment in dictionaries #
        ############################################

        myr_area = calculate_area_over_clip(temp_myr_clip)
        myr_areas[i] = myr_area

        grass_area = calculate_area_over_clip(temp_grass_clip)
        grass_areas[i] = grass_area

        mountain_area = calculate_area_over_clip(temp_mountain_clip)
        mountain_areas[i] = mountain_area

        forest_11_area = calculate_area_over_clip(temp_forest_11)
        forest_11_areas[i] = forest_11_area

        forest_13_area = calculate_area_over_clip(temp_forest_13)
        forest_13_areas[i] = forest_13_area

        forest_14_area = calculate_area_over_clip(temp_forest_14)
        forest_14_areas[i] = forest_14_area

        forest_ar50_area = calculate_area_over_clip(temp_forest_ar50)
        forest_ar50_areas[i] = forest_ar50_area

        myr_ar50_area = calculate_area_over_clip(temp_myr_ar50)
        myr_ar50_areas[i] = myr_ar50_area

        mountain_ar50_area = calculate_area_over_clip(temp_mountain_ar50)
        mountain_ar50_areas[i] = mountain_ar50_area

        nitrogen_kommune.removeSelection()

        #####################################################################################
        # Calculate area percentages and insert in nitrogen_kommune layer's attribute table #
        #####################################################################################

    with edit(nitrogen_kommune):
        for i, feat in enumerate(nitrogen_kommune.getFeatures()):

            lnr_value = feat.attribute('lnr')
            print('kommune: lnr value is: ' + str(lnr_value))

            # dictionary with areas per rectangle fragment
            area_dict = {}

            feat.setAttribute('area_rect', rect_areas[i])
            feat.setAttribute('myr_area', myr_areas[i])
            feat.setAttribute('grass_area', grass_areas[i])
            feat.setAttribute('mountain_area', mountain_areas[i])
            feat.setAttribute('forest_11_area', forest_11_areas[i])
            feat.setAttribute('forest_13_area', forest_13_areas[i])
            feat.setAttribute('forest_14_area', forest_14_areas[i])
            feat.setAttribute('forest_ar50_area', forest_ar50_areas[i])
            feat.setAttribute('myr_ar50_area', myr_ar50_areas[i])
            feat.setAttribute('mountain_ar50_area', mountain_ar50_areas[i])

            myr_perc = myr_areas[i] / rect_areas[i] * 100
            grass_perc = grass_areas[i] / rect_areas[i] * 100
            mountain_perc = mountain_areas[i] / rect_areas[i] * 100
            forest_11_perc = forest_11_areas[i] / rect_areas[i] * 100
            forest_13_perc = forest_13_areas[i] / rect_areas[i] * 100
            forest_14_perc = forest_14_areas[i] / rect_areas[i] * 100
            forest_ar50_perc = forest_ar50_areas[i] / rect_areas[i] * 100
            myr_ar50_perc = myr_ar50_areas[i] / rect_areas[i] * 100
            mountain_ar50_perc = mountain_ar50_areas[i] / rect_areas[i] * 100

            feat.setAttribute('myr_area_perc', myr_perc)
            feat.setAttribute('grass_area_perc', grass_perc)
            feat.setAttribute('mountain_area_perc', mountain_perc)
            feat.setAttribute('forest_11_area_perc', forest_11_perc)
            feat.setAttribute('forest_13_area_perc', forest_13_perc)
            feat.setAttribute('forest_14_area_perc', forest_14_perc)
            feat.setAttribute('forest_ar50_area_perc', forest_ar50_perc)
            feat.setAttribute('myr_ar50_area_perc', myr_ar50_perc)
            feat.setAttribute('mountain_ar50_area_perc', mountain_ar50_perc)
            nitrogen_kommune.updateFeature(feat)

            #####################################################################
            # populate the dictionary containing ares of a rectangular fragment #
            #####################################################################

            area_dict['area_rect'] = rect_areas[i]
            if myr_areas[i]:
                area_dict['myr_area'] = myr_areas[i]
            else:
                area_dict['myr_area'] = 0
            if grass_areas[i]:
                area_dict['grass_area'] = grass_areas[i]
            else:
                area_dict['grass_area'] = 0
            if mountain_areas[i]:
                area_dict['mountain_area'] = mountain_areas[i]
            else:
                area_dict['mountain_area'] = 0
            if forest_11_areas[i]:
                area_dict['forest_11_area'] = forest_11_areas[i]
            else:
                area_dict['forest_11_area'] = 0
            if forest_13_areas[i]:
                area_dict['forest_13_area'] = forest_13_areas[i]
            else:
                area_dict['forest_13_area'] = 0
            if forest_14_areas[i]:
                area_dict['forest_14_area'] = forest_14_areas[i]
            else:
                area_dict['forest_14_area'] = 0
            if forest_ar50_areas[i]:
                area_dict['forest_ar50_area'] = forest_ar50_areas[i]
            else:
                area_dict['forest_ar50_area'] = 0
            if myr_ar50_areas[i]:
                area_dict['myr_ar50_area'] = myr_ar50_areas[i]
            else:
                area_dict['myr_ar50_area'] = 0
            if mountain_ar50_areas[i]:
                area_dict['mountain_ar50_area'] = mountain_ar50_areas[i]
            else:
                area_dict['mountain_ar50_area'] = 0
            area_dict['myr_area_perc'] = myr_perc
            area_dict['grass_area_perc'] = grass_perc
            area_dict['mountain_area_perc'] = mountain_perc
            area_dict['forest_11_area_perc'] = forest_11_perc
            area_dict['forest_13_area_perc'] = forest_13_perc
            area_dict['forest_14_area_perc'] = forest_14_perc
            area_dict['forest_ar50_area_perc'] = forest_ar50_perc
            area_dict['myr_ar50_area_perc'] = myr_ar50_perc
            area_dict['mountain_ar50_area_perc'] = mountain_ar50_perc

            # append the area dictionary to a list with key = rectangle identifier
            rect_frag_area_dict[lnr_value].append(area_dict)

    print(rect_frag_area_dict)

    # add new fields for containing areas to nitrogen output layer
    n_provider = nitrogen.dataProvider()
    n_provider.addAttributes([QgsField("area_rect", QVariant.Double)])
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
    nitrogen.updateFields()
    nitrogen.commitChanges()

    with edit(nitrogen):
        for i, feat in enumerate(nitrogen.getFeatures()):

            lnr_value = feat.attribute('lnr')
            print('global: lnr value is: ' + str(lnr_value))

            ##################################################################################################
            # sum areas of rectangle fragments and populate the attribute table of the final nitrogen output #
            ##################################################################################################

            if rect_frag_area_dict[lnr_value]:
                area_rect = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
                myr_area = sum([a_dict['myr_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                grass_area = sum([a_dict['grass_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                mountain_area = sum([a_dict['mountain_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                forest_11_area = sum([a_dict['forest_11_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                forest_13_area = sum([a_dict['forest_13_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                forest_14_area = sum([a_dict['forest_14_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                forest_ar50_area = sum([a_dict['forest_ar50_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                myr_ar50_area = sum([a_dict['myr_ar50_area'] for a_dict in rect_frag_area_dict[lnr_value]])
                mountain_ar50_area = sum([a_dict['mountain_ar50_area'] for a_dict in rect_frag_area_dict[lnr_value]])

                feat.setAttribute('area_rect', area_rect)
                feat.setAttribute('myr_area', myr_area)
                feat.setAttribute('grass_area', grass_area)
                feat.setAttribute('mountain_area', mountain_area)
                feat.setAttribute('forest_11_area', forest_11_area)
                feat.setAttribute('forest_13_area', forest_13_area)
                feat.setAttribute('forest_14_area', forest_14_area)
                feat.setAttribute('forest_ar50_area', forest_ar50_area)
                feat.setAttribute('myr_ar50_area', myr_ar50_area)
                feat.setAttribute('mountain_ar50_area', mountain_ar50_area)

                myr_perc = myr_area / area_rect * 100
                grass_perc = grass_area / area_rect * 100
                mountain_perc = mountain_area / area_rect * 100
                forest_11_perc = forest_11_area / area_rect * 100
                forest_13_perc = forest_13_area / area_rect * 100
                forest_14_perc = forest_14_area / area_rect * 100
                forest_ar50_perc = forest_ar50_area / area_rect * 100
                myr_ar50_perc = myr_ar50_area / area_rect * 100
                mountain_ar50_perc = mountain_ar50_area / area_rect * 100

                feat.setAttribute('myr_area_perc', myr_perc)
                feat.setAttribute('grass_area_perc', grass_perc)
                feat.setAttribute('mountain_area_perc', mountain_perc)
                feat.setAttribute('forest_11_area_perc', forest_11_perc)
                feat.setAttribute('forest_13_area_perc', forest_13_perc)
                feat.setAttribute('forest_14_area_perc', forest_14_perc)
                feat.setAttribute('forest_ar50_area_perc', forest_ar50_perc)
                feat.setAttribute('myr_ar50_area_perc', myr_ar50_perc)
                feat.setAttribute('mountain_ar50_area_perc', mountain_ar50_perc)
                nitrogen.updateFeature(feat)

    print("Hello again Simon! Processing completed!")










