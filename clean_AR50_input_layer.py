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

    # Greet Simon!
    print("Hello Simon! Starting the processing now!")

    project = QgsProject.instance()

    project.removeAllMapLayers()

    ar50_troendelag = QgsVectorLayer(working_directory +
                                     '/Input_AR50_layers/AR50_50_5e8c55.shp', 'ar50_troendelag',
                                     'ogr')
    project.addMapLayer(ar50_troendelag)

    alg = u'native:fixgeometries'
    params = {"INPUT": ar50_troendelag,
                "OUTPUT": working_directory + '/Input_AR50_layers/clean_ar50_troendelag.gpkg'}
    processing.run(alg, params)

    ar50_clean_troendelag = QgsVectorLayer(
        working_directory + '/Input_AR50_layers/clean_ar50_troendelag.gpkg',
            'clean_ar50_troendelag', 'ogr')
    project.addMapLayer(ar50_clean_troendelag)