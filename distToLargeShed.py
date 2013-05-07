import arcpy, os, re

# rDir = r"C:\Program Files\R\R-2.14.1\bin\x64"
rDir = arcpy.GetParameterAsText(0)
rDir = '"' + rDir 
downScript = arcpy.GetParameterAsText(1)
edgesTable=arcpy.GetParameterAsText(2)
traceid=arcpy.GetParameterAsText(3)
reachField=arcpy.GetParameterAsText(4)
lengthField=arcpy.GetParameterAsText(5)
damField=arcpy.GetParameterAsText(6)
watershedArea=arcpy.GetParameterAsText(7)
shedThreshold=arcpy.GetParameterAsText(8)
relationshipTable=arcpy.GetParameterAsText(9)
fromid=arcpy.GetParameterAsText(10)
toid=arcpy.GetParameterAsText(11)
outputTable=arcpy.GetParameterAsText(12)

cmdString = rDir + '\\Rscript.exe" ' + downScript + " "  + edgesTable + " " + traceid + " " + reachField + " " + lengthField + " " + damField + " " + watershedArea + " " + shedThreshold + " " + relationshipTable+ " " + fromid + " " + toid + " " + outputTable

os.system(cmdString)
