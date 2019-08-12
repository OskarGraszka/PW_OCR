
# PW_OCR

<img src="images\qgis-logo.png" alt="qgis" width="200">

QGIS processing algorithm which recognizes text from raster images inside input polygon features and saves as attribute value of output layer.

PW_OCR_ADVENCED script processes in different way than [*PW_OCR_ADVANCED*](https://github.com/OskarGraszka/PW_OCR_ADVANCED). Check specifications of both scripts to choose better one for your applications.
## Python Tesseract
PW_OCR script usues [*Pytesseract*](https://github.com/madmaze/pytesseract) library and requires its installation.
After installation you have to update path to your *Tesseract* directory at the beginning of the script.
```Python
// path to your tesseract installation directory.
pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
```
You may set *Pytesseract* configuration (page segmentation mode and OCR engine model) using comboboxes of script graphical interface, but if you want to use language other than polish, you have to edit line below in the code:
```Python
text = pytesseract.image_to_string(img, lang='pol', config=self.config)
```

## Algorithm

![Schema](images/Schemat1.png "Schema")

This algorithm iterates over all input polygon features and processes them according to this scheme:
- Exporting feature as separate *shapefile* in temporary file location.
- Clipping raster overlaying the feature to the already made *shapefile* object boundaries and saving it into temporary file location (using *GDAL* library).
- Regonizing text on the clipped raster image (*Pytesseract* library).
- Adding recognized text as attribute value to output feature field.

#
![screen](images/schema1.gif)
#

## Parameters
<dd>
<b>Input polygon layer</b>
<dd>The features used to recognize text inside them.</dd> 
<br><b>Text output field</b>
<dd>The field in the input table in which the recognized text will be add.</dd> 
<br><b>Run for all raster layers</b>
<dd>The algorithm will recognize text from all active raster layers, if checked.</dd> 
<br><b>Input raster layer</b>
<dd>If above checkbox unchecked, the algorithm will recognize text only from this raster layer.
<br>In case of multiband raster images, the only first band will be used.</dd> 
<br><b>Page Segmentation Mode</b>
<dd><i>Tesseract</i> Page Segmentation Mode.</dd> 
<br><b>OCR Engine Model</b>
<dd><i>Tesseract</i> OCR Engine Model.</dd> 
<br><b>Remove comma</b>
<dd>If comma is the last character in recognized text, it will be removed.</dd> 
<br><b>Temporary files location</b>
<dd>Location of such transitional files like image translated to 8bit TIFF, image clipped to the single feature and shapefile contains only one feature. These files are created during iterating over all input features.</dd> 
<br><b>Output layer</b>
<dd>Location of the output layer with filled text attribute.</dd>
</dd>

## See also

[*PW_OCR_ADVANCED*](https://github.com/OskarGraszka/PW_OCR_ADVANCED)

[*PW_ABBREVIATIONS*](https://github.com/OskarGraszka/PW_ABBREVIATIONS)