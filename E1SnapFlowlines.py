#Run this file to check to see if streams cross the confluence of lakes and/or waterbodies
#To fix errors, either split features at boundaries (if cross is long) or adjust features so
#they snap to the edge of each feature

import arcpy
from arcpy import env

env.overwriteOutput = True


############inputs 1
#tempws=r'C:\Users\menuzd\Documents\GIS_24kAttribution\temp'
#inLakes=r'C:\Users\menuzd\Documents\GIS_24kAttribution\Hydro24Current\networklakes08092012.shp'
#inStreams=r'C:\Users\menuzd\Documents\GIS_24kAttribution\Hydro24Current\flowlines08102012.shp'
#outErrors=r'C:\Users\menuzd\Documents\GIS_24kAttribution\temp\ConfluenceError3.shp'
##########################
tempws = arcpy.GetParameter(0)
inLakes=arcpy.GetParameter(1)
inStreams=arcpy.GetParameter(2)
outErrors=arcpy.GetParameter(3)

####
env.workspace =tempws
#Select stream features that intersect lakes in order to make the intersect process proceed faster
arcpy.AddMessage("Selecting stream features that intersect lakes")
arcpy.MakeFeatureLayer_management(inStreams, "streams.lyr", "","","")
arcpy.SelectLayerByLocation_management ("streams.lyr", "INTERSECT", inLakes, "", "NEW_SELECTION")
arcpy.CopyFeatures_management ("streams.lyr", "streamIntersect.shp","","","","")
#Intersect stream features with lake features
arcpy.AddMessage("Intersecting stream features with lake features")
arcpy.Intersect_analysis(["streamIntersect.shp", inLakes], "lakeIntersect.shp","ALL","","LINE")
arcpy.MakeFeatureLayer_management("lakeIntersect.shp", "lakeIntersect.lyr", "","","")
#Select out features that are not identical to original lines
arcpy.AddMessage("Select features not identical to original streams")
arcpy.SelectLayerByLocation_management ("lakeIntersect.lyr", "ARE_IDENTICAL_TO", "streamIntersect.shp", "", "NEW_SELECTION")
arcpy.SelectLayerByAttribute_management ("lakeIntersect.lyr", "SWITCH_SELECTION", "")
arcpy.CopyFeatures_management ("lakeIntersect.lyr", "streamErrors.shp","","","","")
#Select out features in original linework that have errors
arcpy.AddMessage("Select final file of errors")
arcpy.SelectLayerByLocation_management ("streams.lyr", "SHARE_A_LINE_SEGMENT_WITH", "streamErrors.shp", "", "NEW_SELECTION")
arcpy.CopyFeatures_management ("streams.lyr", outErrors,"","","","")

arcpy.DeleteFeatures_management("streamIntersect.shp")
arcpy.DeleteFeatures_management("lakeIntersect.shp")
arcpy.DeleteFeatures_management("streamErrors.shp")

#arcpy.Clip_analysis ("streamIntersect.shp", inLakes, "streamClip1.shp", "")
#arcpy.MakeFeatureLayer_management("streamClip1.shp", "streamClip.lyr", "","","")
#arcpy.SelectLayerByLocation_management ("streamClip.lyr", "ARE_IDENTICAL_TO", "streamIntersect.shp", "", "NEW_SELECTION")
#arcpy.SelectLayerByAttribute_management ("streamClip.lyr", "SWITCH_SELECTION", "")
#arcpy.CopyFeatures_management ("streamClip.lyr", "streamErrors.shp","","","","")
#arcpy.SelectLayerByLocation_management ("streams.lyr", "SHARE_A_LINE_SEGMENT_WITH", "streamErrors.shp", "", "NEW_SELECTION")
#arcpy.CopyFeatures_management ("streams.lyr", outErrors,"","","","")
#arcpy.DeleteFeatures_management("streamClip.shp")
#arcpy.DeleteFeatures_management("streamIntersect.shp")







