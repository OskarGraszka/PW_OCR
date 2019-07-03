# -*- coding: utf-8 -*-

from PyQt5.QtCore import QCoreApplication
from qgis.utils import iface
from osgeo import gdal
import os
import sys
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterField,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFolderDestination,
                       QgsFeatureRequest,
                       QgsSpatialIndex,
                       QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsProject,
                       #QgsProcessingContext
                       )
import processing

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

'''Attention! Attention! All personel! You have to set path to your tesseract installation directory!'''
pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'


class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    RASTER_INPUT = 'RASTER INPUT'
    FIELD = 'FIELD'
    ALL_ACTIVE_RASTERS = 'ALL ACTIVE RASTERS'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExampleProcessingAlgorithm()

    def name(self):
        return 'pw_ocr'

    def displayName(self):
        return self.tr('PW OCR')

    def group(self):
        return self.tr('PW')

    def groupId(self):
        return 'pw'

    def shortHelpString(self):
        help = """This algorithm recognizes text from raster images inside input polygon features and saves as attribute value of output layer.\
        <hr>
        <b>Input polygon layer</b>\
        <br>The features used to recognize text inside them.\
        <br><br><b>Text output field</b>\
        <br>The field in the input table in which the recognized text will be add.\
        <br><br><b>Run for all raster layers</b>\
        <br>The algorithm will recognize text from all active raster layers, if checked.\
        <br><br><b>Input raster layer</b>\
        <br>If above checkbox unchecked, the algorithm will recognize text only from this raster layer.\
        <br>In case of multiband raster images, the only first band will be used.\
        <br><br><b>Page Segmentation Mode</b>\
        <br><i>Tesseract</i> Page Segmentation Mode.\
        <br><br><b>OCR Engine Model</b>\
        <br><i>Tesseract</i> OCR Engine Model.\
        <br><br><b>Remove comma</b>\
        <br>If comma is the last character in recognized text, it will be removed.\
        <br><br><b>Temporary files location</b>\
        <br>Location of such transitional files like image translated to 8bit TIFF, image clipped to the single feature and shapefile contains only one feature. These files are created during iterating over all input features.\
        <br><br><b>Output layer</b>\
        <br>Location of the output layer with filled text attribute.\
        """
        return self.tr(help)

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input polygon layer'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.FIELD,
                self.tr('Text output field'),
                parentLayerParameterName = self.INPUT,
                type = QgsProcessingParameterField.DataType.String
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ALL_ACTIVE_RASTERS,
                self.tr('Run for all raster layers')
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.RASTER_INPUT,
                self.tr('Input raster layer'),
                optional = True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                'PSM',
                self.tr('Page Segmentation Mode'),
                options = [
                    'Orientation and script detection (OSD) only.',
                    'Automatic page segmentation with OSD.',
                    'Automatic page segmentation, but no OSD, or OCR.',
                    'Fully automatic page segmentation, but no OSD. (Default if no config)',
                    'Assume a single column of text of variable sizes.',
                    'Assume a single uniform block of vertically aligned text.',
                    'Assume a single uniform block of text.',
                    'Treat the image as a single text line.',
                    'Treat the image as a single word.',
                    'Treat the image as a single word in a circle.',
                    'Treat the image as a single character.',
                    'Sparse text. Find as much text as possible in no particular order.',
                    'Sparse text with OSD.',
                    'Raw line. Treat the image as a single text line, bypassing hacks that are Tesseract-specific.'
                ],
                defaultValue = 7
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                'OEM',
                self.tr('OCR Engine Model'),
                options = [
                    'Legacy Tesseract',
                    'LSTM',
                    '2',
                    '3'
                ],
                defaultValue = 1
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                'Remove_comma',
                self.tr('Remove comma'),
                True
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                '',
                self.tr('Temporary files location'),
                optional = True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        self.feature_source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )
        raster_lyr = self.parameterAsRasterLayer(
            parameters,
            self.RASTER_INPUT,
            context
        )
        all_rasters = self.parameterAsBool(
            parameters,
            self.ALL_ACTIVE_RASTERS,
            context
        )
        temp_path = self.parameterAsString(
            parameters,
            '',
            context
        )
        self.dest_field = self.parameterAsString(
            parameters,
            self.FIELD,
            context
        )
        psm = self.parameterAsInt(
            parameters,
            'PSM',
            context
        )
        oem = self.parameterAsInt(
            parameters,
            'OEM',
            context
        )
        self.comma = self.parameterAsBool(
            parameters,
            'Remove_comma',
            context
        )
        (self.sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            self.feature_source.fields(),
            self.feature_source.wkbType(),
            self.feature_source.sourceCrs()
        )
        self.source_layer = self.feature_source.materialize(QgsFeatureRequest())
        feedback.pushInfo('Temporary files path: ' + str(temp_path))
        self.source_encod = self.source_layer.dataProvider().encoding()
        '''context.setDefaultEncoding(self.source_encod)
        self.output_encod = context.defaultEncoding()
        
        feedback.pushInfo('sys.getdefaultencoding(): ' + sys.getdefaultencoding())
        feedback.pushInfo('in: ' + self.source_encod + ', out: ' + self.output_encod)'''
        
        if self.source_layer == None:
            list = QgsProject.instance().mapLayersByName(self.feature_source.sourceName())
            for lyr in list:
                if self.feature_source.sourceCrs() == lyr.sourceCrs():
                    self.source_layer = lyr
                    
        #feedback.pushInfo('self.source_layer.name(): ' + self.source_layer.name())
    
        if self.feature_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        if raster_lyr is None and not all_rasters:
            feedback.pushInfo('\nNo raster layer selected!\n')
            raise QgsProcessingException(self.invalidSourceError(parameters, self.RASTER_INPUT))
        self.output_temp_tif = os.path.normpath(os.path.join(temp_path,'output.tif'))
        self.output_temp_shp = os.path.normpath(os.path.join(temp_path,'each_feature.shp'))
        self.output_temp_page = os.path.normpath(os.path.join(temp_path,'current_page.tif'))
        
        '''here is tesseract config string'''
        self.config = '--psm '+str(psm)+' --oem '+str(oem)
        feedback.pushInfo('Tessearct config: ' + self.config)
        
        '''creating temporary shp file, necessary for clipping'''
        self.crs = self.feature_source.sourceCrs().authid()
        layer = QgsVectorLayer("multipolygon?crs="+self.crs+"&field=id:integer", "temporary layer", "memory")
        QgsVectorFileWriter.writeAsVectorFormat(layer, self.output_temp_shp, self.source_encod, self.feature_source.sourceCrs(), "ESRI Shapefile", False)
        self.temp_shp_layer = QgsVectorLayer(self.output_temp_shp, "temp", "ogr")
        

        features = self.feature_source.getFeatures(QgsFeatureRequest())

        self.index = QgsSpatialIndex()
        for feat in features:
            self.index.insertFeature(feat)

        feedback.pushInfo('\nprocessing time calculating...\n')
        n=[]
        if not all_rasters and raster_lyr:
            n = self.index.intersects(raster_lyr.extent())
        else:
            for layer in iface.mapCanvas().layers():
                if layer.type() == 1 :
                    n = n + self.index.intersects(layer.extent())
        self.total = len(n)
        self.actual = 0
        if self.total>0: feedback.setProgress(self.actual/self.total*100)

                    
        if not all_rasters:
            self.OnThisRaster(feedback, raster_lyr)
        else:
            for layer in iface.mapCanvas().layers():
                if feedback.isCanceled(): break
                if layer.type() == 1 :
                    self.OnThisRaster(feedback, layer)
        
        return {'Recognized': str(self.actual)}
        
    def OnThisRaster(self, feedback, Raster_lyr):
        
        idsList = self.index.intersects(Raster_lyr.extent())
        if idsList:
            translateopts = gdal.TranslateOptions(
                            outputType=gdal.GDT_Byte, # Eight bit unsigned integer
                            bandList=[1], # Notice that exports only first band
                            format='GTiff'
                            )
            ds = gdal.Translate(self.output_temp_page, Raster_lyr.source(), options=translateopts)
            if ds is not None: ds = 'image translated to GTiff'
            else: ds = '<red> something went wrong with translating to GTiff'
            feedback.pushCommandInfo('\nComputing image ' + str(Raster_lyr.name()) + '\n' + str(ds) + '\n')
            for id in idsList:
                #Gdyby tutaj się udało wkomponować coś jak getFeaturebyID byłoby pewnie szybciej
                for feat in self.feature_source.getFeatures(QgsFeatureRequest()):
                    if int(feat.id()) == id:
                        self.OnThisFeature(feedback, feat, self.output_temp_page)
                        break
                
    def OnThisFeature(self, feedback, feat, Raster_lyr_source):

        pr = self.temp_shp_layer.dataProvider()
        for temp_feature in pr.getFeatures():
            pr.deleteFeatures([temp_feature.id()])
        pr.addFeatures( [ feat ] )
            
        self.ClipRasterByPolygon(feedback, Raster_lyr_source, self.output_temp_shp, self.output_temp_tif)
        img = Image.open(self.output_temp_tif)
        text = pytesseract.image_to_string(img, lang='pol', config=self.config)
        if self.comma:
            if text[-1:] == ',': text = text[:-1]
            
        feat[self.dest_field] = text#.encode('utf8')#.decode('CP1250')

        self.sink.addFeature(feat, QgsFeatureSink.FastInsert)

        self.actual = self.actual + 1
        feedback.setProgress(self.actual/self.total*100)
        feedback.setProgressText(str(self.actual)+'/'+str(self.total) + '       ' +'id:  ' + str(feat.id()))
        feedback.pushCommandInfo(text)
        #feedback.pushCommandInfo(str(type(text)))
        
    def ClipRasterByPolygon(self, feedback, rasterPath, polygonPath, outputPath):

        warpopts = gdal.WarpOptions(
                            outputType=gdal.GDT_Byte, 
                            srcSRS=self.crs,
                            cutlineDSName = polygonPath,
                            cropToCutline=True,
                            dstNodata = 255.0,# to jest rozwiązanie wszystkich światowych problemów z dziedziny OCR
                            )
        ds = gdal.Warp(outputPath, rasterPath, options=warpopts)
        #feedback.pushCommandInfo(str(ds))