from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
import processing
from processing.core.Processing import Processing
import os

Processing.initialize()


def run_script(iface):

    # Set the encoding
    QgsSettings().setValue('/Processing/encoding', 'utf-8')

    # Set the working environment folders. Requires input data being organized in a precise structure
    working_directory = "C:/Data/Simon"

    #Greet Simon!
    print("Hello Simon! Starting the processing now!")

    project = QgsProject.instance()

    project.removeAllMapLayers()


    ar5_directory = os.fsencode(working_directory + '/input_AR5_layers_all/')

    for file in os.listdir(ar5_directory):
        filename = os.fsdecode(file)
        kommune_name = filename[15:-19]
        print("processing " + kommune_name)

        if kommune_name == 'Rindal':
            kommune_num = '1567'
        else:
            kommune_num = filename[10:].split('_', 1)[0]

        ar5_kommune = QgsVectorLayer(
            working_directory + '/Input_AR5_layers_all/Basisdata_' + kommune_num + '_' + kommune_name + '_25832_FKB-AR5_SOSI/Basisdata_' + kommune_num + '_' + kommune_name + '_25832_FKB-AR5_SOSI_polygon.shp',
            'AR5_' + kommune_name, 'ogr')
        project.addMapLayer(ar5_kommune)

        alg = u'native:fixgeometries'
        params = {"INPUT": ar5_kommune,
                  "OUTPUT": working_directory + '/clean_input_AR5_layers/clean_ar5_' +kommune_num+'_'+kommune_name+'.gpkg'}
        processing.run(alg, params)

        ar5_kommune_clean = QgsVectorLayer(
            working_directory + '/clean_input_AR5_layers/clean_ar5_' + kommune_num + '_' + kommune_name + '.gpkg',
            'ar5_clean_' + kommune_name, 'ogr')
        project.addMapLayer(ar5_kommune_clean)




