import arcpy, os, re

# rDir = r"C:\Program Files\R\R-2.14.1\bin\x64"
rDir = arcpy.GetParameterAsText(0)
rDir = '"' + rDir 
connectScript = arcpy.GetParameterAsText(1)
maxDist=arcpy.GetParameterAsText(2)
lakeMin=arcpy.GetParameterAsText(3)
lakeMax=arcpy.GetParameterAsText(4)
relationshipTable=arcpy.GetParameterAsText(5)
fromID=arcpy.GetParameterAsText(6)
toID=arcpy.GetParameterAsText(7)
flowlineData=arcpy.GetParameterAsText(8)
IDcol=arcpy.GetParameterAsText(9)
reachField=arcpy.GetParameterAsText(10)
lengthField=arcpy.GetParameterAsText(11)
damField=arcpy.GetParameterAsText(12)
stopTraceField=arcpy.GetParameterAsText(13)
lakeAreaField=arcpy.GetParameterAsText(14)
#none of these columns should have from or to in their names, just to be safe
outputTable=arcpy.GetParameterAsText(15)


cmdString = rDir + '\\Rscript.exe" ' + connectScript + " "  + maxDist + " " + lakeMin + " " + lakeMax + " " + relationshipTable + " " + fromID + " " + toID + " " + flowlineData + " " + IDcol+ " " + reachField + " " + lengthField + " " + damField + " " + stopTraceField+ " " + lakeAreaField + " " + outputTable

os.system(cmdString)
