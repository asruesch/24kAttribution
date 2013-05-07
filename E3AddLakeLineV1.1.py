#Run this file to look for waterbody features that are connected to hydrologic network but are missing internal lines

import arcpy
from arcpy import env

env.overwriteOutput = True


############inputs 1
#tempws=r'C:\Users\menuzd\Documents\GIS_24kAttribution\temp'
#waterbody=r'C:\Users\menuzd\Documents\GIS_24kAttribution\Hydro24Current\waterbodies08092012.shp'
#inStreams=r'C:\Users\menuzd\Documents\GIS_24kAttribution\Hydro24Current\flowlines08102012.shp'
#outErrors=r'C:\Users\menuzd\Documents\GIS_24kAttribution\temp\addlines.shp'
#dist=0
#addtype="addtype"
##########################
tempws=arcpy.GetParameter(0)
waterbody=arcpy.GetParameter(1)
inStreams=arcpy.GetParameter(2)
outErrors=arcpy.GetParameter(3)
outNetwork=arcpy.GetParameter(4)
dist=arcpy.GetParameter(5)
addtype=arcpy.GetParameter(6)

####
env.workspace =tempws
#Select out lakes within a specified distance of streams
arcpy.AddMessage("Selecting lake features that should be networked")
arcpy.MakeFeatureLayer_management(waterbody, "waterbody.lyr", "","","")
arcpy.SelectLayerByLocation_management ("waterbody.lyr", "WITHIN_A_DISTANCE", inStreams, "{0} METERS".format(dist), "NEW_SELECTION")
arcpy.CopyFeatures_management ("waterbody.lyr", "nearWB.shp","","","","")
#Select out remaining "isolated" lakes
arcpy.AddMessage("Selecting isolated lake features")
arcpy.SelectLayerByAttribute_management ("waterbody.lyr", "SWITCH_SELECTION","")
arcpy.CopyFeatures_management ("waterbody.lyr", "isolatedWB.shp","","","","")
#Select stream features that intersect lakes in order to make the intersect process proceed faster
arcpy.AddMessage("Selecting streams near lakes")
arcpy.MakeFeatureLayer_management(inStreams, "streams.lyr", "","","")
arcpy.SelectLayerByLocation_management ("streams.lyr", "INTERSECT", "nearWB.shp", "", "NEW_SELECTION")
arcpy.CopyFeatures_management ("streams.lyr", "streamsreduced.shp","","","","")
#Intersect stream features with lake features
arcpy.AddMessage("Intersecting streams with lakes")
arcpy.Intersect_analysis(["streamsreduced.shp", "nearWB.shp"], "streamLakeIntersect.shp","ALL","","LINE")
#Join nearWB features back to intersecting line features based on FID
arcpy.AddMessage("Identifying lakes that need lines")
arcpy.AddField_management ("streamLakeIntersect.shp", "network", "SHORT", "", "", 1)
arcpy.CalculateField_management ("streamLakeIntersect.shp", "network", 1, "VB")

#this works but it is really really slow
#arcpy.JoinField_management ("nearWB.shp","FID","streamLakeIntersect.shp","FID_nearWB", ["network"])
#trying to use add join to speed up process
arcpy.env.qualifiedFieldNames=False
arcpy.MakeFeatureLayer_management("nearWB.shp", "nearWB.lyr", "","","")
arcpy.MakeFeatureLayer_management("streamLakeIntersect.shp", "streamLakeIntersect.lyr", "","","")
arcpy.AddJoin_management("nearWB.lyr","FID","streamLakeIntersect.lyr","FID_nearWB","KEEP_ALL")
arcpy.SelectLayerByAttribute_management("nearWB.lyr","NEW_SELECTION","network IS NULL")
arcpy.CopyFeatures_management ("nearWB.lyr", "addline1","","","","")
#this creates file of networked waterbodies!! create output for it
arcpy.SelectLayerByAttribute_management("nearWB.lyr","SWITCH_SELECTION")
arcpy.CopyFeatures_management ("nearWB.lyr", outNetwork,"","","","")

#delete confusing fields from addline1, basically, want all nearWB fields and only network from streamLakeIntersect
#first, figure out how many fields are in each input file
nearwbcount=len(arcpy.ListFields("nearWB.shp"))
intersectcount=len(arcpy.ListFields("streamLakeIntersect.shp"))
#create values for beginning and end of fields that we want to delete
start=nearwbcount
end=nearwbcount+intersectcount-2
#create list of fields and then loop through to get all field names out
fieldObjList = arcpy.ListFields("addline1.shp")
fieldNameList = []
for field in fieldObjList:
     fieldNameList.append(field.name)
#create list of fields we want to delete
delfields=fieldNameList[start:end]
#delete fields of interest
arcpy.AddMessage("Deleting unnecessary lines")
arcpy.DeleteField_management ("addline1.shp", delfields)

arcpy.AddField_management("addline1.shp", addtype, "SHORT", "", "", 1)
arcpy.CalculateField_management ("addline1.shp", addtype, 1)

#Identify isolated polygons that intersect network or potentially networked polygons
arcpy.AddMessage("Identifying isolated lakes near networked lakes")
arcpy.MakeFeatureLayer_management("isolatedWB.shp", "isolatedWB.lyr", "","","")
arcpy.SelectLayerByLocation_management ("isolatedWB.lyr", "INTERSECT", "nearWB.shp", "", "NEW_SELECTION")
arcpy.CopyFeatures_management ("isolatedWB.lyr", "addline2","","","","")
arcpy.AddField_management ("addline2.shp", addtype, "SHORT", "", "", 1)
arcpy.CalculateField_management ("addline2.shp", addtype, 2, "VB")
arcpy.AddMessage("Merging features")
arcpy.Merge_management(["addline1.shp", "addline2.shp"], outErrors)

#arcpy.AddMessage("Deleting extra files")
#arcpy.DeleteFeatures_management("addlines1.shp")
#arcpy.DeleteFeatures_management("addlines2.shp")
#arcpy.DeleteFeatures_management("isolatedWB.shp")
#arcpy.DeleteFeatures_management("join.shp")
#arcpy.DeleteFeatures_management("nearWB.shp")
#arcpy.DeleteFeatures_management("streamLakeIntersect.shp")
#arcpy.DeleteFeatures_management("streamsreduced.shp")
