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
Processing.initialize()


def run_script(iface):

    # Set the encoding
    QgsSettings().setValue('/Processing/encoding', 'utf-8')

    # Set the working environment folder. Requires input data and output folders being organized in a precise structure
    working_directory = "C:\Data\Simon"

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
    ar5_trondheim = QgsVectorLayer(working_directory + '/Input_AR5_layers/Basisdata_5001_Trondheim_25832_FKB-AR5_SOSI/Basisdata_5001_Trondheim_25832_FKB-AR5_SOSI_polygon.shp', 'AR5_trondheim', 'ogr')
    nitrogen = QgsVectorLayer(working_directory + '/nitrogen/nitrogen_repro_clip.shp', 'nitrogen', 'ogr')

    project.addMapLayer(n50)
    project.addMapLayer(ar50_troendelag)
    project.addMapLayer(ar5_trondheim)
    project.addMapLayer(nitrogen)


    # Selecting and filtering out the Troendelag fylke polygon from AdministrativeOmråder
    # TODO: this step could not be necessary: Administrative borders are implicit in AR5 input data per Kommune. Maybe simpler
    query = "Kommunenum LIKE '50%'"
    selection = n50.getFeatures(QgsFeatureRequest().setFilterExpression(query))
    n50.select([k.id() for k in selection])
    QgsVectorFileWriter.writeAsVectorFormat(n50, working_directory + '/Outputs/script/n50_trondelag_kommune', "utf-8",
                                            n50.crs(), "GPKG", onlySelected=True)
    n50_trondelag_kommune = QgsVectorLayer(working_directory + '/Outputs/script/n50_trondelag_kommune.gpkg',
                                           'n50_trondelag_kommunes', 'ogr')
    project.addMapLayer(n50_trondelag_kommune)

    # Selecting only the Trondheim Kommune
    query2 = u"navn = 'Trondheim'"
    selection2 = n50_trondelag_kommune.getFeatures(QgsFeatureRequest().setFilterExpression(query2))
    n50_trondelag_kommune.select([k.id() for k in selection2])
    QgsVectorFileWriter.writeAsVectorFormat(n50_trondelag_kommune, working_directory + '/Outputs/script/n50_trondheim',
                                            "utf-8", n50_trondelag_kommune.crs(), "GPKG", onlySelected=True)
    n50_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/n50_trondheim.gpkg', 'n50_trondheim', 'ogr')
    project.addMapLayer(n50_trondheim)

    # Clip nitrogen over Trondheim Kommune
    alg = 'qgis:clip'
    params = {"INPUT": nitrogen, "OVERLAY": n50_trondheim,
              "OUTPUT": working_directory + '/Outputs/script/nitrogen_trondheim_clip.gpkg'}
    processing.run(alg, params)

    nitrogen_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/nitrogen_trondheim_clip.gpkg',
                                        'nitrogen_trondheim', 'ogr')
    project.addMapLayer(nitrogen_trondheim)

    # clip ar50 over Trondheim Kommune
    alg_clip = u'qgis:clip'
    params = {"INPUT": ar50_troendelag, "OVERLAY": n50_trondheim,
              "OUTPUT": working_directory + '/Outputs/script/ar50_trondheim_clip.gpkg'}
    processing.run(alg_clip, params)

    ar50_trondheim_clip = QgsVectorLayer(
        working_directory + '/Outputs/script/ar50_trondheim_clip.gpkg', 'ar50_trondheim_clip',
        'ogr')
    project.addMapLayer(ar50_trondheim_clip)

    # add forest limit layer
    # TODO: Clean the layer from geometries errors before time
    forest_limit = QgsVectorLayer(working_directory + '/forest_limit/skoggrense_tr_poly_1_re_enkel10.shp',
                                  'forest_limit', 'ogr')
    project.addMapLayer(forest_limit)

    query3 = u"ARTYPE = '50' OR ARTYPE = '99'"
    selection3 = ar5_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query3))
    ar5_trondheim.select([k.id() for k in selection3])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_trondheim,
                                            working_directory + '/Outputs/script/ar5_mountain_rough_trondheim',
                                            "utf-8", ar50_trondheim_clip.crs(), "GPKG", onlySelected=True)
    ar5_mountain_rough_trondheim = QgsVectorLayer(
        working_directory + '/Outputs/script/ar5_mountain_rough_trondheim.gpkg', 'ar5_mountain_rough_trondheim', 'ogr')
    project.addMapLayer(ar5_mountain_rough_trondheim)

    # removing ar50 mountain polygons bi difference with the forest limit layer
    # TODO: looks like there are some geometry errors in one of the 2 layers. Check!

    # run the Fix geometries alg on rough montain trondheim
    # TODO: It was not this layer. It was the forest limit having issues. clean it and keep out of any loop


    # run the Fix geometries alg on forest limit
    #alg = u'native:fixgeometries'
    #params = {"INPUT": forest_limit,
    #          "OUTPUT": working_directory + '/Outputs/script/forest_limit_fixed.gpkg'}
    #processing.run(alg, params)

    # Importing the forest limit layer, cleaned
    # TODO: maybe just substitute the original, keeping same name?
    forest_limit_fixed = QgsVectorLayer(
        working_directory + '/Outputs/script/forest_limit_fixed.gpkg',
        'forest_limit_fixed',
        'ogr')
    project.addMapLayer(forest_limit_fixed)

    # Run the difference between mountain areas and forest line
    alg_diff = u'qgis:clip'
    params = {"INPUT": ar5_mountain_rough_trondheim, "OVERLAY": forest_limit_fixed,
              "OUTPUT": working_directory + '/Outputs/script/ar5_mountain_clean_trondheim.gpkg'}
    processing.run(alg_diff, params)

    ar5_mountain_clean_trondheim = QgsVectorLayer(
        working_directory + '/Outputs/script/ar5_mountain_clean_trondheim.gpkg', 'ar5_mountain_clean_trondheim', 'ogr')
    project.addMapLayer(ar5_mountain_clean_trondheim)

    # Selecting forest type from AR5 (ARTYPE 30, which includes more detailed classes: ARSKOGBON)
    query4 = u"ARTYPE = '30'"
    selection4 = ar5_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query4))
    ar5_trondheim.select([k.id() for k in selection4])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_trondheim, working_directory + '/Outputs/script/ar5_skog_trondheim',
                                            "utf-8", ar5_trondheim.crs(), "GPKG", onlySelected=True)

    ar5_skog_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar5_skog_trondheim.gpkg',
                                        'ar5_skog_trondheim', 'ogr')
    project.addMapLayer(ar5_skog_trondheim)

    # remove previous filter selection from ar50_trondheim_clip
    ar50_trondheim_clip.removeSelection()

    # Selecting forest type from AR50, which should have priority over AR5
    # TODO: Is it true? AR50 should have priority over AR5? shouldn't be the opposite?
    query5 = u"ARTYPE = '30'"
    selection5 = ar50_trondheim_clip.getFeatures(QgsFeatureRequest().setFilterExpression(query5))
    ar50_trondheim_clip.select([k.id() for k in selection5])
    QgsVectorFileWriter.writeAsVectorFormat(ar50_trondheim_clip,
                                            working_directory + '/Outputs/script/ar50_skog_trondheim', "utf-8",
                                            ar50_trondheim_clip.crs(), "GPKG", onlySelected=True)

    ar50_skog_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar50_skog_trondheim.gpkg',
                                        'ar50_skog_trondheim', 'ogr')
    project.addMapLayer(ar50_skog_trondheim)

    # Remove selection from AR5 and AR50
    ar5_trondheim.removeSelection()
    ar50_trondheim_clip.removeSelection()

    # myr in ar50
    query6 = u"ARTYPE = '60'"
    selection6 = ar50_trondheim_clip.getFeatures(QgsFeatureRequest().setFilterExpression(query6))
    ar50_trondheim_clip.select([k.id() for k in selection6])
    QgsVectorFileWriter.writeAsVectorFormat(ar50_trondheim_clip,
                                            working_directory + '/Outputs/script/ar50_myr_trondheim', "utf-8",
                                            ar50_trondheim_clip.crs(), "GPKG", onlySelected=True)

    ar50_myr_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar50_myr_trondheim.gpkg',
                                         'ar50_myr_trondheim', 'ogr')
    project.addMapLayer(ar50_myr_trondheim)

    # myr in ar5
    query7 = u"ARTYPE = '60'"
    selection7 = ar5_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query7))
    ar5_trondheim.select([k.id() for k in selection7])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_trondheim,
                                            working_directory + '/Outputs/script/ar5_myr_trondheim', "utf-8",
                                            ar5_trondheim.crs(), "GPKG", onlySelected=True)

    ar5_myr_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar5_myr_trondheim.gpkg',
                                        'ar5_myr_trondheim', 'ogr')
    project.addMapLayer(ar5_myr_trondheim)

    # Again, remove selection
    ar5_trondheim.removeSelection()

    # Semi-natural grassland AR5
    query9 = u"ARTYPE = '23'"
    selection9 = ar5_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query9))
    ar5_trondheim.select([k.id() for k in selection9])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_trondheim,
                                            working_directory + '/Outputs/script/ar5_grass_trondheim', "utf-8",
                                            ar5_trondheim.crs(), "GPKG", onlySelected=True)

    ar5_grass_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar5_grass_trondheim.gpkg',
                                       'ar5_grass_trondheim', 'ogr')
    project.addMapLayer(ar5_grass_trondheim)

    ar5_trondheim.removeSelection()

    # Filter Low-productive forest from forest layer (Arskogbon = 11)
    query11 = u"ARSKOGBON = '11'"
    selection11 = ar5_skog_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query11))
    ar5_skog_trondheim.select([k.id() for k in selection11])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_skog_trondheim,
                                            working_directory + '/Outputs/script/ar5_skog_11_trondheim', "utf-8",
                                            ar5_skog_trondheim.crs(), "GPKG", onlySelected=True)

    ar5_skog_11_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar5_skog_11_trondheim.gpkg',
                                           'ar5_skog_11_trondheim', 'ogr')
    project.addMapLayer(ar5_skog_11_trondheim)

    ar5_skog_trondheim.removeSelection()

    # Filter  Medium-productive forest from forest layer (Arskogbon = 13)
    query12 = u"ARSKOGBON = '13'"
    selection12 = ar5_skog_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query12))
    ar5_skog_trondheim.select([k.id() for k in selection12])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_skog_trondheim,
                                            working_directory + '/Outputs/script/ar5_skog_13_trondheim', "utf-8",
                                            ar5_skog_trondheim.crs(), "GPKG", onlySelected=True)

    ar5_skog_13_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar5_skog_13_trondheim.gpkg',
                                           'ar5_skog_13_trondheim', 'ogr')
    project.addMapLayer(ar5_skog_13_trondheim)

    ar5_skog_trondheim.removeSelection()

    # Filter  High-productive forest from forest layer (Arskogbon = 14)
    query13 = u"ARSKOGBON = '14'"
    selection13 = ar5_skog_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query13))
    ar5_skog_trondheim.select([k.id() for k in selection13])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_skog_trondheim,
                                            working_directory + '/Outputs/script/ar5_skog_14_trondheim', "utf-8",
                                            ar5_skog_trondheim.crs(), "GPKG", onlySelected=True)

    ar5_skog_14_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar5_skog_14_trondheim.gpkg',
                                           'ar5_skog_14_trondheim', 'ogr')
    project.addMapLayer(ar5_skog_14_trondheim)

    ar5_skog_trondheim.removeSelection()

    # Calculate the diff (skog ar50 - skog ar5)
    # TODO: Also here some geometry errors. Solve it on input layers
    #alg = u'qgis:difference'
    #params = {"INPUT": ar50_skog_trondheim, "OVERLAY": ar5_skog_trondheim,
    #          "OUTPUT": working_directory + '/Outputs/script/ar50_skog_diff_trondheim.gpkg'}
    #processing.run(alg, params)

    #ar50_skog_diff_trondheim = QgsVectorLayer(
    #    working_directory + '/Outputs/script/ar50_skog_diff_trondheim.gpkg', 'ar50_skog_diff_trondheim', 'ogr')
    #project.addMapLayer(ar50_skog_diff_trondheim)

    ar5_trondheim.removeSelection()

    # Filtering also ARTYPE = 50 to compare with mountain from AR50
    # Semi-natural grassland AR5
    query10 = u"ARTYPE = '50'"
    selection10 = ar5_trondheim.getFeatures(QgsFeatureRequest().setFilterExpression(query10))
    ar5_trondheim.select([k.id() for k in selection10])
    QgsVectorFileWriter.writeAsVectorFormat(ar5_trondheim,
                                            working_directory + '/Outputs/script/ar5_open_trondheim', "utf-8",
                                            ar5_trondheim.crs(), "GPKG", onlySelected=True)

    ar5_open_trondheim = QgsVectorLayer(working_directory + '/Outputs/script/ar5_open_trondheim.gpkg',
                                         'ar5_open_trondheim', 'ogr')
    project.addMapLayer(ar5_open_trondheim)

    #####################################################################################
    # Now we need to calculate area percentage per nitrogen rectangular clipped polygon #
    #####################################################################################

    # Add new fields to nitrogen_trondheim attributte table
    n_provider = nitrogen_trondheim.dataProvider()
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
    nitrogen_trondheim.updateFields()

    feats_nit = [feat for feat in nitrogen_trondheim.getFeatures()]

    rect_areas = {}
    myr_areas = {}
    grass_areas = {}
    mountain_areas = {}
    forest_11_areas = {}
    forest_13_areas = {}
    forest_14_areas = {}

    # iterating over rectangular polygons of nitrogen layer
    for i, feat in enumerate(feats_nit):
        area_rect = 0
        calculator = QgsDistanceArea()
        geom1 = feat.geometry()
        if geom1.isMultipart() is False:
            pol = geom1.asPolygon()
            if len(pol)>0:
                area_rect = calculator.measurePolygon(pol[0])
        else:  # is Multipart
            multi = geom1.asMultiPolygon()
            for polyg in multi:
                area_rect = area_rect + calculator.measurePolygon(polyg[0])
        rect_areas[i] = area_rect

        # selecting each rectangular nitrogen polygon one by one
        nitrogen_trondheim.select(feat.id())
        temp_feat_layer = nitrogen_trondheim.materialize(QgsFeatureRequest().setFilterFids( nitrogen_trondheim.selectedFeatureIds()))
        project.addMapLayer(temp_feat_layer)

        # process grassland
        params = {"INPUT": ar5_grass_trondheim, "OVERLAY": temp_feat_layer,
                  "OUTPUT": working_directory + '/Outputs/script/trondheim/ar5_grass_trondheim_clip_'+str(i)+'.gpkg'}
        processing.run(alg_clip, params)
        temp_grass_clip = QgsVectorLayer(working_directory + '/Outputs/script/trondheim/ar5_grass_trondheim_clip_'+str(i)+'.gpkg', 'myr_clip_trondheim_'+str(i), 'ogr')

        # process Myr
        params = {"INPUT": ar5_myr_trondheim, "OVERLAY": temp_feat_layer,
                  "OUTPUT": working_directory + '/Outputs/script/trondheim/ar5_myr_trondheim_clip_' + str(i) + '.gpkg'}
        processing.run(alg_clip, params)
        temp_myr_clip = QgsVectorLayer(
            working_directory + '/Outputs/script/trondheim/ar5_myr_trondheim_clip_' + str(i) + '.gpkg',
            'myr_clip_trondheim_' + str(i), 'ogr')

        # process mountain
        params = {"INPUT": ar5_mountain_clean_trondheim, "OVERLAY": temp_feat_layer,
                  "OUTPUT": working_directory + '/Outputs/script/trondheim/ar5_mountain_trondheim_clip_' + str(i) + '.gpkg'}
        processing.run(alg_clip, params)
        temp_mountain_clip = QgsVectorLayer(
            working_directory + '/Outputs/script/trondheim/ar5_mountain_trondheim_clip_' + str(i) + '.gpkg',
            'mountain_clip_trondheim_' + str(i), 'ogr')

        ar5_trondheim.removeSelection()

        ###########################
        #  FOREST SUB-CLASSES ###
        ###########################

        # process skog with ARskogbon = 11
        params = {"INPUT": ar5_skog_11_trondheim, "OVERLAY": temp_feat_layer,
                  "OUTPUT": working_directory + '/Outputs/script/trondheim/ar5_skog_11_trondheim_clip_' + str(
                      i) + '.gpkg'}
        processing.run(alg_clip, params)
        temp_ar5_skog_11_trondheim_clip = QgsVectorLayer(
            working_directory + '/Outputs/script/trondheim/ar5_skog_11_trondheim_clip_' + str(i) + '.gpkg',
            'ar5_skog_11_trondheim_clip_' + str(i), 'ogr')

        # Remove selection from AR5 and AR50
        ar5_trondheim.removeSelection()

        # process skog with ARskogbon = 13
        params = {"INPUT": ar5_skog_13_trondheim, "OVERLAY": temp_feat_layer,
                  "OUTPUT": working_directory + '/Outputs/script/trondheim/ar5_skog_13_trondheim_clip_' + str(
                      i) + '.gpkg'}
        processing.run(alg_clip, params)
        temp_ar5_skog_13_trondheim_clip = QgsVectorLayer(
            working_directory + '/Outputs/script/trondheim/ar5_skog_13_trondheim_clip_' + str(i) + '.gpkg',
            'ar5_skog_13_trondheim_clip_' + str(i), 'ogr')

        # process skog with ARskogbon = 14
        params = {"INPUT": ar5_skog_14_trondheim, "OVERLAY": temp_feat_layer,
                  "OUTPUT": working_directory + '/Outputs/script/trondheim/ar5_skog_14_trondheim_clip_' + str(
                      i) + '.gpkg'}
        processing.run(alg_clip, params)
        temp_ar5_skog_14_trondheim_clip = QgsVectorLayer(
            working_directory + '/Outputs/script/trondheim/ar5_skog_14_trondheim_clip_' + str(i) + '.gpkg',
            'ar5_skog_14_trondheim_clip_' + str(i), 'ogr')


        def calculate_area_over_clip(input_layer):
            area = 0
            with edit(input_layer):
                for featc in input_layer.getFeatures():
                    calculator = QgsDistanceArea()

                    #calculator.setEllipsoid('WGS84')
                    #calculator.setEllipsoidalMode(True)

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

        # Store areas per fragment in dictionaries

        myr_area = calculate_area_over_clip(temp_myr_clip)
        myr_areas[i] = myr_area

        grass_area = calculate_area_over_clip(temp_grass_clip)
        grass_areas[i] = grass_area

        mountain_area = calculate_area_over_clip(temp_mountain_clip)
        mountain_areas[i] = mountain_area

        forest_11_area = calculate_area_over_clip(temp_ar5_skog_11_trondheim_clip)
        forest_11_areas[i] = forest_11_area

        forest_13_area = calculate_area_over_clip(temp_ar5_skog_13_trondheim_clip)
        forest_13_areas[i] = forest_13_area

        forest_14_area = calculate_area_over_clip(temp_ar5_skog_14_trondheim_clip)
        forest_14_areas[i] = forest_14_area

        # TODO: remove this. Just for testing
        project.addMapLayer(temp_myr_clip)

        nitrogen_trondheim.removeSelection()


    # Calculate area percentages and insert in nitrogen_kommune layer's attribute table
    with edit(nitrogen_trondheim):
        for i, feat in enumerate(nitrogen_trondheim.getFeatures()):
            try:
                feat.setAttribute('area_rect', rect_areas[i])
                feat.setAttribute('myr_area', myr_areas[i])
                feat.setAttribute('grass_area', grass_areas[i])
                feat.setAttribute('mountain_area', mountain_areas[i])
                feat.setAttribute('forest_11_area', forest_11_areas[i])
                feat.setAttribute('forest_13_area', forest_13_areas[i])
                feat.setAttribute('forest_14_area', forest_14_areas[i])

                myr_perc = myr_areas[i]/rect_areas[i]*100
                grass_perc = grass_areas[i]/rect_areas[i]*100
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
                nitrogen_trondheim.updateFeature(feat)
            except ValueError:
                print("Error setting Area")
                return

    print("Hello again Simon! Processing completed!")

