#Code to assign reach IDs to streams and lakes and 
#to determine which non-lake waterbody features will be included as seeds
#Features input into this tool had some modification and clean-up before tool use
#make sure features will breach HUC12 boundary and/or add greater boundary for HUC12

import arcpy
from arcpy import env
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
env.overwriteOutput = True


def fieldNames(feature):
	"""Returns list of field names in a GIS feature, 
	list is called names"""
	fields=arcpy.ListFields(feature)
	names=[]
	for f in fields:
		names.append(f.name)
	del f, fields
	return names

def checkForName(nameList, name):
	"""Checks to see if a given value is on a list of names"""
	flag=False
	for item in nameList:
		if item==name:
			flag=True
	return flag
	
def fieldInFeature(feature, fieldName):
	"""Checks to see if a given field name is in attribute table of a shapefile
	Returns True or False"""
	nameList=fieldNames(feature)
	return checkForName(nameList, fieldName)


###############################################################################
tempws = arcpy.GetParameterAsText(0) #folder where temporary files will be stored

inStreams=arcpy.GetParameterAsText(1) #shapefile of line features
streamid=arcpy.GetParameterAsText(2) #unique identifer of the line features
seed=arcpy.GetParameterAsText(3) #name of column that indicates whether or not a feature should be included as seed based on 0s and 1s
#"seed" was based on previous work determining whether features were primary, non-landlocked features within the study area we were interested in
primary=arcpy.GetParameterAsText(4) #used when selecting landlocked features that we wanted to include in study

inWB=arcpy.GetParameterAsText(5) #shapefile of all waterbodies (lakes, double line streams, etc)
wbid=arcpy.GetParameterAsText(6)  #unique identifier of the waterbodies

lakeID=arcpy.GetParameterAsText(7) #field in waterbody shapefile that is marked 1 if a feature is a feature we want to include as an independent seed
#(in our case, all seeds were lakes >=5 acres) and 0 if not a seed feature

network=arcpy.GetParameterAsText(8) #name of new column that will be created be script that determines whether or not
#waterbody feature is connected to the network

reachid=arcpy.GetParameterAsText(9) #the column name to be added that will be in the unique identifer of the feature
aggID=arcpy.GetParameterAsText(10)  #the column name to describe how reaches would be aggregated up into confluence- bounded segments

studyArea=arcpy.GetParameterAsText(11) #shapefile of the boundary of the study area

outLakes=arcpy.GetParameterAsText(12) #output file of the selected lakes, both networked and isolated
outNetworkWB=arcpy.GetParameterAsText(13) #output file of networked non-lake waterbodies
#this should be corrected to include waterbodies attached to included landlocked streams
outGLWB=arcpy.GetParameterAsText(14)  #lakes that will be excluded from analysis
#this is just a check, it shows features that are not included in analysis because they are under what we are considering the Great Lakes, based on the NHD HUC delineation
outputStreams=arcpy.GetParameterAsText(15)  #output shapefile of all of the streams, including all of the
#non-landlocked primary streams as well as streams attached to landlocked lakes
outVertex=arcpy.GetParameterAsText(16) #output shapefile of all of the confluence points, used later
#for preventing spurs

#great lakes ID code
greatLakes=arcpy.GetParameterAsText(17) #polygon shapefile of Great Lakes HUCs, used to determine which features #are under the great lakes
colName=arcpy.GetParameterAsText(18) #name of column added that will determine which features have their centroids under the great lakes


##############################################################################
env.scratchWorkspace = tempws
env.workspace = tempws

#1) Selecting out stream features that are considered networked streams, based on input column
arcpy.AddMessage("Selecting initial seed streams")
arcpy.Select_analysis(inStreams, "selectStreams.shp", "{0} =1".format(seed))


#2 Removing all Great Lakes lines except those necessary to breach HUC12 boundary
arcpy.MakeFeatureLayer_management ("selectStreams.shp", "nonGreatLakes.lyr")
arcpy.MakeFeatureLayer_management (greatLakes, "greatLakes.lyr")
arcpy.AddMessage("Selecting non-Great Lakes lines")
arcpy.SelectLayerByLocation_management ("nonGreatLakes.lyr", "HAVE_THEIR_CENTER_IN", greatLakes, "", "NEW_SELECTION")
arcpy.SelectLayerByAttribute_management ("nonGreatLakes.lyr", "SWITCH_SELECTION")
arcpy.CopyFeatures_management("nonGreatLakes.lyr", "nonGreatLakes.shp")
arcpy.AddField_management("selectStreams.shp",colName,"SHORT","1","#","#","#","NON_NULLABLE","NON_REQUIRED","#")
arcpy.MakeFeatureLayer_management ("selectStreams.shp", "netStreams.lyr")
arcpy.AddMessage("Selecting breach Great Lake lines")
arcpy.SelectLayerByLocation_management ("netStreams.lyr", "HAVE_THEIR_CENTER_IN", greatLakes, "", "NEW_SELECTION")
arcpy.CalculateField_management ("netStreams.lyr", colName, 1, "VB","")
arcpy.SelectLayerByAttribute_management ("netStreams.lyr", "SWITCH_SELECTION")
arcpy.MakeFeatureLayer_management ("nonGreatLakes.shp", "nonGreatLakes.lyr")
arcpy.SelectLayerByLocation_management ("netStreams.lyr", "INTERSECT", "nonGreatLakes.lyr", "", "ADD_TO_SELECTION")
arcpy.CopyFeatures_management("netStreams.lyr", "netStreams.shp")


#3) Determine which waterbody features are networked
arcpy.AddMessage("Converting line midpoints to points")
arcpy.FeatureVerticesToPoints_management("netStreams.shp", "netStreamPts.shp", "MID")
arcpy.MakeFeatureLayer_management ("netStreamPts.shp", "netStreamsPts.lyr", "", "", "")
arcpy.CopyFeatures_management(inWB, "tempWB.shp")
arcpy.AddField_management("tempWB.shp", network,"SHORT","1","#","#","#","NON_NULLABLE","NON_REQUIRED","#")
arcpy.MakeFeatureLayer_management ("tempWB.shp", "tempWB.lyr", "", "", "")
arcpy.AddMessage("Determining which lakes are networked")
arcpy.SelectLayerByLocation_management ("tempWB.lyr", "COMPLETELY_CONTAINS", "netStreamsPts.lyr", "", "NEW_SELECTION")
arcpy.CalculateField_management ("tempWB.lyr", network, 1, "VB","")
arcpy.SelectLayerByAttribute_management("tempWB.lyr", "CLEAR_SELECTION")

#4 Select out only those features that overlap study area boundary or overlap networked streams (in case some features meander
#just outside of state lines along Mississippi, etc.)
arcpy.AddMessage("Selecting waterbody feautures in the study area")
arcpy.MakeFeatureLayer_management (studyArea, "studyArea.lyr")
arcpy.SelectLayerByLocation_management ("tempWB.lyr", "INTERSECT", "studyArea.lyr", "", "NEW_SELECTION")
arcpy.AddMessage("Selecting waterbody features that intersect networked streams")
arcpy.MakeFeatureLayer_management ("netStreams.shp", "netStreams.lyr", "", "", "")
arcpy.SelectLayerByLocation_management ("tempWB.lyr", "INTERSECT", "netStreams.lyr", "", "ADD_TO_SELECTION")
arcpy.CopyFeatures_management("tempWB.lyr", "statusWB", "","","","")


#5) Remove lake features that are under the Great Lakes HUC and create a separate GL output file so we can look at what is removed
arcpy.AddMessage("Removing waterbodies under the Great Lakes")
arcpy.FeatureToPoint_management ("statusWB.shp", "statusWBpts.shp", "INSIDE")
arcpy.MakeFeatureLayer_management ("statusWBpts.shp", "statusWBpts.lyr")
arcpy.MakeFeatureLayer_management (greatLakes, "greatLakes.lyr", "", "", "")
arcpy.SelectLayerByLocation_management ("statusWBpts.lyr", "WITHIN", "greatLakes.lyr", "", "NEW_SELECTION")
arcpy.MakeFeatureLayer_management ("statusWB.shp", "statusWB.lyr")
arcpy.SelectLayerByLocation_management ("statusWB.lyr", "CONTAINS", "statusWBpts.lyr", "", "NEW_SELECTION")
arcpy.CopyFeatures_management("statusWB.lyr", outGLWB)
arcpy.SelectLayerByAttribute_management("statusWB.lyr", "SWITCH_SELECTION")
arcpy.CopyFeatures_management("statusWB.lyr", "finalWB")


#6) Select out features that are considered lakes and are >= 5 acres (for now will assume that is all in one column)
arcpy.AddMessage("Selecting out lakes")
arcpy.Select_analysis("finalWB.shp", "finalLakes.shp", "{0} =1".format(lakeID))


#7) Select all streamlines that are connected to isolated lakes
arcpy.AddMessage("Selecting isolated lakes")
arcpy.Select_analysis("finalLakes.shp", "isolatedLakes.shp", "{0} =0".format(network))
#Select streams lines that are not networked and are not secondary
arcpy.MakeFeatureLayer_management(inStreams, "otherStreams.lyr")
arcpy.SelectLayerByAttribute_management("otherStreams.lyr", "NEW_SELECTION",'"{0}" =0'.format(seed))
arcpy.SelectLayerByAttribute_management("otherStreams.lyr", "SUBSET_SELECTION",'"{0}" =1'.format(primary))
arcpy.CopyFeatures_management("otherStreams.lyr", "otherStreams.shp")

#Select initial features in "otherStreams.shp" that intersect isolatedLakes
arcpy.AddMessage("Selecting lines that intersect isolated lakes")
arcpy.MakeFeatureLayer_management ("isolatedLakes.shp", "isolatedLakes.lyr")
arcpy.MakeFeatureLayer_management ("otherStreams.shp", "otherStreams.lyr")
arcpy.SelectLayerByLocation_management('otherStreams.lyr', 'INTERSECT', 'isolatedLakes.lyr', "", 'NEW_SELECTION')

arcpy.AddMessage("Iteratively selecting lines that touch selected lines")                                 
#run loop to iteratively select all features that intersect features that intersect isolated lakes
selectionCount = int(arcpy.GetCount_management('otherStreams.lyr').getOutput(0))
lastCount = 0

while selectionCount <> lastCount:
    lastCount = selectionCount
    arcpy.SelectLayerByLocation_management('otherStreams.lyr', 'INTERSECT', 'otherStreams.lyr', "", 'ADD_TO_SELECTION')
    selectionCount = int(arcpy.GetCount_management('otherStreams.lyr').getOutput(0))



#8  add field to distinguish isolated stream seeds from other seeds
arcpy.CopyFeatures_management("otherStreams.lyr", "otherStreamsAdd.shp", "","","","")
arcpy.AddField_management("otherStreamsAdd.shp","seedtype","TEXT","","","20","","NON_NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management ("otherStreamsAdd.shp","seedtype", '"isolated stream"', "VB","")
#merge selected other streams with networked streams as final stream seed layer
arcpy.Merge_management (["netStreams.shp", "otherStreamsAdd.shp"], "seedStreams.shp")


#9) Separating lake and non-lake stream lines
arcpy.AddMessage("Selecting out features under lakes")
arcpy.MakeFeatureLayer_management ("seedStreams.shp", "seedStreams.lyr", "", "", "")
arcpy.MakeFeatureLayer_management ("finalLakes.shp", "finalLakes.lyr", "", "", "")
arcpy.SelectLayerByLocation_management ("seedStreams.lyr", "HAVE_THEIR_CENTER_IN", "finalLakes.lyr", "", "NEW_SELECTION")
arcpy.CopyFeatures_management("seedStreams.lyr", "lakeLines", "","","","")

arcpy.AddMessage("Selecting out remaining features")
arcpy.SelectLayerByLocation_management ("seedStreams.lyr", "","", "", "SWITCH_SELECTION")
arcpy.CopyFeatures_management ("seedStreams.lyr", "finalStreams", "","","","")


#10) Creating crosswalk for streams under lakes
arcpy.AddMessage("Assigning reach IDs to streams under lakes")
arcpy.AddField_management("finalLakes.shp",reachid,"LONG","9","#","#","#","NON_NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management ("finalLakes.shp", reachid, "[{0}]".format(wbid), "VB","")

lines="lakeLines.shp"
lakes="finalLakes.shp"

#11) Extract out reach ID from lakes file
arcpy.AddMessage("Field mapping")
lakemapping = arcpy.FieldMappings()
lakemapping.addTable(lakes)
field1=lakemapping.findFieldMapIndex(reachid)
field1map=lakemapping.getFieldMap(field1)
#add all fields from lakeLines file and reachID from other file to fieldMappings
finalmappings = arcpy.FieldMappings()
finalmappings.addTable(lines)
finalmappings.addFieldMap(field1map)
arcpy.AddMessage("Creating crosswalk for streams under lakes")
arcpy.SpatialJoin_analysis(lines,lakes,"lakestreamsxwalk.shp","JOIN_ONE_TO_MANY","KEEP_ALL",finalmappings,"HAVE_THEIR_CENTER_IN","#","#")
arcpy.JoinField_management("finalLakes.shp", reachid, "lakestreamsxwalk.shp", reachid, ["Join_Count"])
arcpy.AddMessage("Adding seed type field")
arcpy.CalculateField_management ("lakestreamsxwalk.shp","seedtype", '"lake"', "VB","")
arcpy.AddField_management("lakestreamsxwalk.shp",aggID,"LONG","9","","","","NON_NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management ("lakestreamsxwalk.shp",aggID, "[{0}]".format(reachid), "VB","")


#12) Convert streams into confluence-bounded segments
arcpy.AddMessage("Dissolving streams")
arcpy.Dissolve_management("finalStreams.shp", "reaches.shp",colName,"#","SINGLE_PART","UNSPLIT_LINES")

arcpy.FeatureVerticesToPoints_management ("reaches.shp", outVertex, "BOTH_ENDS")

#13) Add aggregate ID field
arcpy.AddMessage("Adding aggregate ID field")
arcpy.AddField_management("reaches.shp", aggID,"LONG","9","#","#","#","NON_NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management("reaches.shp",aggID,"[FID]+300000000","VB","#")


#14) Create stream crosswalk
arcpy.AddMessage("Creating crosswalk for stream reaches")
reach="reaches.shp"
stream="finalStreams.shp"
#Extract out reach ID and agg ID from reaches file
reachmapping = arcpy.FieldMappings()
reachmapping.addTable(reach)
aggidfield=reachmapping.findFieldMapIndex(aggID)
aggidfieldmap=reachmapping.getFieldMap(aggidfield)
#add all fields from lakeLines file and reachID from other file to fieldMappings
xwalkmappings = arcpy.FieldMappings()
xwalkmappings.addTable(stream)
xwalkmappings.addFieldMap(aggidfieldmap)

arcpy.SpatialJoin_analysis(stream,"reaches.shp","streamsxwalk.shp","JOIN_ONE_TO_MANY","KEEP_ALL",xwalkmappings,"HAVE_THEIR_CENTER_IN","#","#")
arcpy.MakeFeatureLayer_management ("streamsxwalk.shp", "streamsxwalk.lyr")
arcpy.SelectLayerByAttribute_management("streamsxwalk.lyr", "NEW_SELECTION"," \"seedtype\" = 'stream' ")
arcpy.SelectLayerByAttribute_management("streamsxwalk.lyr", "SWITCH_SELECTION")
arcpy.CalculateField_management("streamsxwalk.lyr", "seedtype",'"stream"', "VB","")                                        


#adding identifer for great lake lines
arcpy.SelectLayerByAttribute_management("streamsxwalk.lyr", "NEW_SELECTION", "{0}=1".format(colName))
arcpy.CalculateField_management("streamsxwalk.lyr", "seedtype", '"Great Lakes"', "VB","")
arcpy.SelectLayerByAttribute_management("streamsxwalk.lyr", "CLEAR_SELECTION")

arcpy.CopyFeatures_management("streamsxwalk.lyr", "streamsxwalkFinal.shp")


#15) Add reach ID field to streams xwalk
arcpy.AddMessage("Adding unique ID field")
arcpy.AddField_management("streamsxwalkFinal.shp", reachid,"LONG","9","#","#","#","NON_NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management("streamsxwalkFinal.shp", reachid, "[{0}]".format(streamid), "VB","")


#16) Create final crosswalk for all stream lines
arcpy.AddMessage("Merging crosswalk into final table")
arcpy.Merge_management(["lakestreamsxwalk.shp", "streamsxwalkFinal.shp"], outputStreams,"#")

#17) Copy out file of lakes
arcpy.CopyFeatures_management("finalLakes.shp", outLakes)

#18) Copy out file of networked WB
arcpy.MakeFeatureLayer_management ("finalWB.shp", "finalWB.lyr")
arcpy.SelectLayerByAttribute_management("finalWB.lyr", "NEW_SELECTION", "{0}=1".format(network))
arcpy.SelectLayerByAttribute_management("finalWB.lyr", "REMOVE_FROM_SELECTION", "{0}=1".format(lakeID))
arcpy.CopyFeatures_management("finalWB.lyr", outNetworkWB)


