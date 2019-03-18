#!/usr/bin/env python
# Customize this starter script by adding code
# to the run_script function. See the Help for
# complete information on how to create a script
# and use Script Runner.

""" The following script loads and extracts land cover area percentages over a nitrogen layer in a Kommune in Trøndelag.
 This script defines a workflow which will be iterated over all the Kommunes in Trøndelag Fylke.
 The script is designed to work with the Script runner plugin in QGIS 3. Note: needs refactoring and generalization """

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
    output_directory = '/new_outputs/'
    nitrogen_outputs = '/nitrogen_outputs/'
    nitrogen_outputs_fullpath = working_directory + output_directory + nitrogen_outputs

    if os.path.isdir(nitrogen_outputs_fullpath):
        pass
    else:
        os.mkdir(nitrogen_outputs_fullpath)

    #Greet Simon!
    print("Hello Simon! Starting the processing now!")
    project = QgsProject.instance()

    # Remove any layer previously existing in current project
    project.removeAllMapLayers()

    # Remove also all groups, if any
    root = project.layerTreeRoot()
    root.removeAllChildren()

    n50 = QgsVectorLayer(working_directory + '/Input_N50_layers/N50_AdministrativeOmråder.shp', 'n50_borders', 'ogr')
    ar50_troendelag = QgsVectorLayer(working_directory + '/Input_AR50_layers/AR50_50_5e8c55.shp', 'ar50_troendelag', 'ogr')
    nitrogen = QgsVectorLayer(working_directory + '/nitrogen/nitrogen_repro_clip.shp', 'nitrogen', 'ogr')
    forest_limit = QgsVectorLayer(working_directory + '/Outputs/script/forest_limit_fixed.gpkg',
                                  'forest_limit', 'ogr')

    project.addMapLayer(n50)
    project.addMapLayer(ar50_troendelag)
    project.addMapLayer(nitrogen)
    project.addMapLayer(forest_limit)


    def query_layer(query, input_layer, output_name):
        selection = input_layer.getFeatures(QgsFeatureRequest().setFilterExpression(query))
        input_layer.select([k.id() for k in selection])
        QgsVectorFileWriter.writeAsVectorFormat(input_layer,
                                                working_directory + output_directory + output_name,
                                                "utf-8", input_layer.crs(), "GPKG", onlySelected=True)
        layer = QgsVectorLayer(working_directory + output_directory + output_name+'.gpkg', output_name, 'ogr')
        project.addMapLayer(layer)
        input_layer.removeSelection()
        return layer

    clip_alg = 'qgis:clip'

    def geoprocess_layer(alg, input_layer, overlay, output_name, add_layer=True):
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

                # this section can be simple if you perform the alg single to multiple from the processing toolbox.
                # Doing so you will not have any multiple Polygon
                # is Multipart
                else:
                    multi = geom.asMultiPolygon()
                    for polyg in multi:
                        area = area + calculator.measurePolygon(polyg[0])

        return area

    rect_frag_area_dict = defaultdict(list)


    ar5_directory = os.fsencode(working_directory + '/Input_AR5_layers/')

    for file in os.listdir(ar5_directory):
        filename = os.fsdecode(file)
        kommune_name = filename[15:-19]
        if kommune_name == 'Rindal':
            kommune_num = '1567'
        else:
            kommune_num = filename[10:].split('_', 1)[0]

        # extract the current kommune's contour polygon
        query = "Kommunenum = '"+kommune_num+"'"
        input_layer = n50
        kommune_border_name = 'n50_'+kommune_name
        print(query)
        print(kommune_border_name)
        n50_kommune = query_layer(query, input_layer, kommune_border_name)

        # clip nitrogen over current kommune
        nitrogen_kommune_name = 'nitrogen_' + kommune_name
        nitrogen_kommune = geoprocess_layer(clip_alg, nitrogen, n50_kommune, nitrogen_kommune_name)

        # clip ar50 over current Kommune
        # TODO: AR50 needs geometry fixing before use
        ar50_kommune_name = 'ar50_' + kommune_name
        geoprocess_layer(clip_alg, ar50_troendelag, n50_kommune, ar50_kommune_name)

        ar5_kommune = QgsVectorLayer(
            working_directory + '/Input_AR5_layers/Basisdata_'+kommune_num+'_'+kommune_name+'_25832_FKB-AR5_SOSI/Basisdata_'+kommune_num+'_'+kommune_name+'_25832_FKB-AR5_SOSI_polygon.shp',
            'AR5_'+kommune_name, 'ogr')
        project.addMapLayer(ar5_kommune)

        # Filtering mountain areas from AR5, not yet clipped by forest limit
        query2 = u"ARTYPE = '50' OR ARTYPE = '99'"
        input_layer = ar5_kommune
        mountain_rough_name = 'ar50_mountain_rough_' + kommune_name
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

        # TODO: query ar50 for forest type, where ar5 is absent (see line 154 in the trondheims script)

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
        query6 = u"ARSKOGBON = '11'"
        input_layer = ar5_forest_kommune
        forest_11_name = 'ar5_skog_11_' + kommune_name
        ar5_forest_11_kommune = query_layer(query6, input_layer, forest_11_name)

        # Filter  Medium-productive forest from forest layer (Arskogbon = 13)
        query7 = u"ARSKOGBON = '13'"
        input_layer = ar5_forest_kommune
        forest_13_name = 'ar5_skog_13_' + kommune_name
        ar5_forest_13_kommune = query_layer(query7, input_layer, forest_13_name)

        # Filter  High-productive forest from forest layer (Arskogbon = 14)
        query8 = u"ARSKOGBON = '14'"
        input_layer = ar5_forest_kommune
        forest_14_name = 'ar5_skog_14_' + kommune_name
        ar5_forest_14_kommune = query_layer(query8, input_layer, forest_14_name)

        #####################################################################################
        # Now we need to calculate area percentage per nitrogen rectangular clipped polygon #
        #####################################################################################

        # Add new fields to nitrogen_trondheim attribute table
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
        nitrogen_kommune.updateFields()

        rect_areas = {}
        myr_areas = {}
        grass_areas = {}
        mountain_areas = {}
        forest_11_areas = {}
        forest_13_areas = {}
        forest_14_areas = {}

        feats_nit = [feat for feat in nitrogen_kommune.getFeatures()]

        # iterating over rectangular polygons of nitrogen layer
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
            #project.addMapLayer(temp_feat_layer)

            # process grassland
            ar5_grass_kommune_clip_name = 'ar5_grass_clip_' + kommune_name + '_' + str(i)
            temp_grass_clip = geoprocess_layer(clip_alg, ar5_grass_kommune, temp_feat_layer, ar5_grass_kommune_clip_name, add_layer=False)

            # process Myr
            ar5_myr_kommune_clip_name = 'ar5_myr_clip_' + kommune_name + '_' + str(i)
            temp_myr_clip = geoprocess_layer(clip_alg, ar5_myr_kommune, temp_feat_layer, ar5_myr_kommune_clip_name, add_layer=False)

            # process mountain
            ar5_mountain_kommune_clip_name = 'ar5_mountain_clip_' + kommune_name + '_' + str(i)
            temp_mountain_clip = geoprocess_layer(clip_alg, ar5_mountain_clean_kommune, temp_feat_layer, ar5_mountain_kommune_clip_name, add_layer=False)

            ###########################
            #  FOREST SUB-CLASSES ###
            ###########################

            # process skog with ARskogbon = 11
            ar5_forest_11_kommune_name = 'ar5_forest_11_kommune_' + kommune_name + '_' + str(i)
            temp_forest_11 = geoprocess_layer(clip_alg, ar5_forest_11_kommune, temp_feat_layer, ar5_forest_11_kommune_name,
                             add_layer=False)

            # process skog with ARskogbon = 13
            ar5_forest_13_kommune_name = 'ar5_forest_13_kommune_' + kommune_name + '_' + str(i)
            temp_forest_13 = geoprocess_layer(clip_alg, ar5_forest_13_kommune, temp_feat_layer, ar5_forest_13_kommune_name,
                             add_layer=False)

            # process skog with ARskogbon = 14
            ar5_forest_14_kommune_name = 'ar5_forest_14_kommune_' + kommune_name + '_' + str(i)
            temp_forest_14 = geoprocess_layer(clip_alg, ar5_forest_14_kommune, temp_feat_layer, ar5_forest_14_kommune_name,
                             add_layer=False)

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

            nitrogen_kommune.removeSelection()

            # Calculate area percentages and insert in nitrogen_kommune layer's attribute table


        with edit(nitrogen_kommune):
            for i, feat in enumerate(nitrogen_kommune.getFeatures()):

                lnr_value = feat.attribute('lnr')
                print('lnr value is: ' + str(lnr_value))

                # This will be a dictionary having as a key the lnr identification number of each rectangle fragment,
                # and as a value a list of dictionaries. Each dictionary in list will contain the area values of a rectangle
                # fragment with the same id of the original whole rectangle.

                area_dict = {}


                try:
                    feat.setAttribute('area_rect', rect_areas[i])
                    feat.setAttribute('myr_area', myr_areas[i])
                    feat.setAttribute('grass_area', grass_areas[i])
                    feat.setAttribute('mountain_area', mountain_areas[i])
                    feat.setAttribute('forest_11_area', forest_11_areas[i])
                    feat.setAttribute('forest_13_area', forest_13_areas[i])
                    feat.setAttribute('forest_14_area', forest_14_areas[i])

                    myr_perc = myr_areas[i] / rect_areas[i] * 100
                    grass_perc = grass_areas[i] / rect_areas[i] * 100
                    mountain_perc = mountain_areas[i] / rect_areas[i] * 100
                    forest_11_perc = forest_11_areas[i] / rect_areas[i] * 100
                    forest_13_perc = forest_13_areas[i] / rect_areas[i] * 100
                    forest_14_perc = forest_14_areas[i] / rect_areas[i] * 100

                    feat.setAttribute('myr_area_perc', myr_perc)
                    feat.setAttribute('grass_area_perc', grass_perc)
                    feat.setAttribute('mountain_area_perc', mountain_perc)
                    feat.setAttribute('forest_11_area_perc', forest_11_perc)
                    feat.setAttribute('forest_13_area_perc', forest_13_perc)
                    feat.setAttribute('forest_14_area_perc', forest_14_perc)
                    nitrogen_kommune.updateFeature(feat)
                except ValueError:
                    print("Error setting Area")
                    return

                # populate the dictionary containing ares of a rectangular fragment
                area_dict['area_rect'] = rect_areas[i]
                area_dict['myr_area'] = myr_areas[i]
                area_dict['grass_area'] = grass_areas[i]
                area_dict['mountain_area'] = mountain_areas[i]
                area_dict['forest_11_area'] = forest_11_areas[i]
                area_dict['forest_13_area'] = forest_13_areas[i]
                area_dict['forest_14_area'] = forest_14_areas[i]
                area_dict['myr_area_perc'] = myr_perc
                area_dict['grass_area_perc'] = grass_perc
                area_dict['mountain_area_perc'] = mountain_perc
                area_dict['forest_11_area_perc'] = forest_11_perc
                area_dict['forest_13_area_perc'] = forest_13_perc
                area_dict['forest_14_area_perc'] =  forest_14_perc

                # append the area dictionary to a a list with key = rectangle identifier
                rect_frag_area_dict[lnr_value].append(area_dict)

    print(rect_frag_area_dict)

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
    nitrogen_kommune.updateFields()

    with edit(nitrogen):
        for i, feat in enumerate(nitrogen.getFeatures()):

            lnr_value = feat.attributes('lnr')
            print('lnr value is: ' + lnr_value)

            # This will be a dictionary having as a key the lnr identification number of each rectangle fragment,
            # and as a value a list of dictionaries. Each dictionary in list will contain the area values of a rectangle
            # fragment with the same id of the original whole rectangle.

            area_rect = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
            myr_area = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
            grass_area = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
            mountain_area = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
            forest_11_area = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
            forest_13_area = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
            forest_14_area = sum([a_dict['area_rect'] for a_dict in rect_frag_area_dict[lnr_value]])
            try:
                feat.setAttribute('area_rect', area_rect)
                feat.setAttribute('myr_area', myr_area)
                feat.setAttribute('grass_area', grass_area)
                feat.setAttribute('mountain_area', mountain_area)
                feat.setAttribute('forest_11_area', forest_11_area)
                feat.setAttribute('forest_13_area', forest_13_area)
                feat.setAttribute('forest_14_area', forest_14_area)

                myr_perc = myr_areas / rect_areas * 100
                grass_perc = grass_areas / rect_areas * 100
                mountain_perc = mountain_areas / rect_areas * 100
                forest_11_perc = forest_11_areas / rect_areas * 100
                forest_13_perc = forest_13_areas / rect_areas * 100
                forest_14_perc = forest_14_areas / rect_areas * 100

                feat.setAttribute('myr_area_perc', myr_perc)
                feat.setAttribute('grass_area_perc', grass_perc)
                feat.setAttribute('mountain_area_perc', mountain_perc)
                feat.setAttribute('forest_11_area_perc', forest_11_perc)
                feat.setAttribute('forest_13_area_perc', forest_13_perc)
                feat.setAttribute('forest_14_area_perc', forest_14_perc)
                nitrogen.updateFeature(feat)
            except ValueError:
                print("Error setting Area")
                return

    print("Hello again Simon! Processing completed!")




