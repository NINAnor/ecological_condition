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
    wilderness_areas = working_directory + '/wilderness areas/'

    # Greet Simon!
    print("Hello Simon! Starting the processing now!")

    project = QgsProject.instance()

    project.removeAllMapLayers()

    ar50_troendelag = QgsVectorLayer(working_directory +
                                     '/Input_AR50_layers/AR50_50_5e8c55.shp', 'ar50_troendelag',
                                     'ogr')
    project.addMapLayer(ar50_troendelag)

    alg_clean = u'native:fixgeometries'


    for file in os.listdir(wilderness_areas):
        filename = os.fsdecode(file)

        if filename.endswith('.shp'):
            print(filename)
            year = filename[4:8]
            print(year)

            inon_layer = QgsVectorLayer(wilderness_areas + 'old_inon/' + filename, 'inon_input_' + year, 'ogr')
            project.addMapLayer(inon_layer)


            params = {"INPUT": inon_layer,
                      "OUTPUT": wilderness_areas + 'inon_clean_' + year + '.gpkg'}
            processing.run(alg_clean, params)

            inon_clean_layer = QgsVectorLayer(wilderness_areas + 'inon_clean_' + year + '.gpkg', 'inon_clean_' + year, 'ogr')
            project.addMapLayer(inon_clean_layer)