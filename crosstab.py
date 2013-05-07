import arcpy, os, re

# rDir = r"C:\Program Files\R\R-2.14.1\bin\x64"
rDir = arcpy.GetParameterAsText(0)
rDir = '"' + rDir 
zoneScript = arcpy.GetParameterAsText(1)
rasterFolder = arcpy.GetParameterAsText(2)
zones = arcpy.GetParameterAsText(3)
outputFolder = arcpy.GetParameterAsText(4)
tempRDir = arcpy.GetParameterAsText(5)
runID = arcpy.GetParameterAsText(6)
zoneType = arcpy.GetParameterAsText(7)
rasterType = arcpy.GetParameterAsText(8)

cmdString = rDir + '\\Rscript.exe" ' + zoneScript + " " + rasterFolder + " " + zones + " " + outputFolder + " " + tempRDir + " " + runID + " " + zoneType + " " + rasterType

os.system(cmdString)

