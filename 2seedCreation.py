#Script that creates raster seeds from lakes, waterbodies and stream lines
#Script also creates raster grid of vertices
#Script is intended to work with output of feature selection

import arcpy
from arcpy import env
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
env.overwriteOutput = True

############################################################################
tempws = arcpy.GetParameterAsText(0) #folder were temporary files are stored
inConfluence=arcpy.GetParameterAsText(1) #input file of confluence points used to prevent spurs
inOtherWB=arcpy.GetParameterAsText(2) #input shapefile of non-lake networked waterbodies that will be included
inReach=arcpy.GetParameterAsText(3) #input shapefile of stream lines (including lines under lakes)
inLakes=arcpy.GetParameterAsText(4) #input shapefile of lakes that will be individual seeds
reachid=arcpy.GetParameterAsText(5) #name of column that is unique identifier of reaches or seeds
inCoast=arcpy.GetParameterAsText(6) #input coastline shapefile for features that will have direct overland runoff rather 
#than only run-off through channels; we use with the Great Lakes and Lake Winnebago; potentially
#could be used for any HUC that is entirely filled by a waterbody and/or for coastal areas
dem=arcpy.GetParameterAsText(7) #dem to snap features to
#these outputs currently are commented out; instead, separate files are created that must be
#merged together outside of the script
inBoundary=arcpy.GetParameterAsText(8)
outSeeds=arcpy.GetParameterAsText(9) #raster seeds
outVertex=arcpy.GetParameterAsText(10) #raster vertices

##############################################################################
env.scratchWorkspace = tempws
env.workspace = tempws

env.outputCoordinateSystem=dem
env.cellSize = dem
env.snapRaster = dem

#1) Create buffered boundary to waterbody features 
arcpy.AddMessage("Buffering input boundary")
arcpy.Buffer_analysis(inBoundary, "bufferBoundary.shp", "1000 Meters", "FULL", "", "ALL", "")
env.extent="bufferBoundary.shp"
arcpy.PolygonToRaster_conversion("bufferBoundary.shp", 'FID', 'bufferBoundary.img', 'MAXIMUM_COMBINED_AREA', "","")
arcpy.AddMessage("Clipping DEM to input features")
demClip = "demClip.img"
arcpy.Clip_management(dem, "#", demClip, "bufferBoundary.img", "#", "")
env.extent="demClip.img"
#select out lake and reach features that intersect HUC boundary
arcpy.AddMessage("Selecting input features")
arcpy.MakeFeatureLayer_management(inReach, "reach.lyr", "","","")
arcpy.SelectLayerByLocation_management ("reach.lyr", "INTERSECT", "bufferBoundary.shp", "", "NEW_SELECTION")
arcpy.CopyFeatures_management ("reach.lyr", "reachOverlap.shp","","","","")
arcpy.MakeFeatureLayer_management(inLakes, "lakes.lyr", "","","")
arcpy.SelectLayerByLocation_management ("lakes.lyr", "INTERSECT", "bufferBoundary.shp", "", "NEW_SELECTION")
arcpy.CopyFeatures_management ("lakes.lyr", "lakesOverlap.shp","","","","")
#clip watershed features by boundary
arcpy.AddMessage("Clipping other waterbodies")
arcpy.Clip_analysis(inOtherWB, "bufferBoundary.shp", "WBOverlap.shp")
arcpy.Clip_analysis(inCoast, "bufferBoundary.shp", "coastOverlap.shp")

#3)Convert input features to rasters
arcpy.AddMessage("Converting reach seeds to raster")
arcpy.PolylineToRaster_conversion ("reachOverlap.shp", reachid, "streams.img", "MAXIMUM_COMBINED_LENGTH" ,"NONE", "")
arcpy.AddMessage("Converting lake seeds to raster")
arcpy.PolygonToRaster_conversion ("lakesOverlap.shp", reachid, "lakeseed.img", "MAXIMUM_COMBINED_AREA",  "NONE","")


#4b Creating raster of vertex points for both stream and lake confluences
arcpy.AddMessage("Creating confluence raster")
arcpy.FeatureToRaster_conversion(inConfluence, "FID", "finalvertex.img")

#5) Combining other waterbodies to streams
#5a) Clip streams by other waterbodies (to prevent incorrect assignments)
#first do a select by location to speed clip up
arcpy.AddMessage("Creating waterbody raster")
arcpy.PolygonToRaster_conversion ("WBOverlap.shp", "FID", "wb.img", "MAXIMUM_COMBINED_AREA",  "NONE","")
arcpy.AddMessage("Clipping reaches by waterbodies")
arcpy.MakeFeatureLayer_management("reachOverlap.shp", "reach.lyr", "","","")
arcpy.SelectLayerByLocation_management ("reach.lyr", "INTERSECT", "WBOverlap.shp", "", "NEW_SELECTION")
arcpy.CopyFeatures_management ("reach.lyr", "reachreduced.shp","","","","")
arcpy.Clip_analysis("reachreduced.shp", "WBOverlap.shp", "reachclip.shp", "")
arcpy.PolylineToRaster_conversion ("reachclip.shp", reachid, "reachclip.img", "MAXIMUM_COMBINED_LENGTH" ,"NONE", "")

#5c Create source raster for cost allocation tool (streams without vertex)
arcpy.AddMessage("Creating source raster")
source=Con(IsNull("finalvertex.img"), "reachclip.img")
source.save("source.img")

#5d Create cost raster
#first create joint file of reaches and waterbodies and set equal to 1
arcpy.AddMessage("Combining reach and waterbody rasters")
streamwb = Con(IsNull("reachclip.img"), "wb.img", "reachclip.img")
streamwb.save("streamwb.img")
arcpy.AddMessage("Building raster attribute table")
arcpy.BuildRasterAttributeTable_management ("streamwb.img", "")
arcpy.AddMessage("Converting to initial cost raster")
cost=Con("streamwb.img", "1", "", "VALUE IS NOT NULL")
cost.save("cost1.img")
#create value of two at point of intersection
arcpy.AddMessage("Creating second cost raster")
cost2=Con("finalvertex.img", "2", "", "VALUE IS NOT NULL")
cost2.save("cost2.img")
#merge two rasters together
arcpy.AddMessage("Creating final cost raster")
finalcost=Con(IsNull("cost2.img"), "cost1.img", "cost2.img")
finalcost.save("finalcost.img")

#5e Allocate waterbodies to stream reaches
arcpy.AddMessage("Allocating waterbodies to stream reaches")
allocate=CostAllocation("source.img", "finalcost.img", "", "", "", "", "")
allocate.save("allocatereach.img")

#5f Fill in No Data values with stream info
arcpy.AddMessage("Filling in No Data values")
#####Determine which way to do this- allocate reach first is the current way this has been done...
###allocating streams first makes more sense, but need to check for potential problems with this
#final=Con(IsNull("streams.img"), "allocatereach.img", "streams.img")
final=Con(IsNull("allocatereach.img"), "streams.img", "allocatereach.img")
final.save("finalreaches.img")


#6 Combining lakes with waterbody and stream seeds, prioritizing lakes
arcpy.AddMessage("Combining streams to lakes")
final=Con(IsNull("lakeseed.img"), "finalreaches.img", "lakeseed.img")

#7 Melding final seeds with coastline seeds
coast= [f.getValue("FID") for f in arcpy.SearchCursor("coastOverlap.shp")]
if len(coast)>0:
	final.save("comboSeeds.img")
	arcpy.AddMessage("Converting coastline to raster")
	arcpy.PolylineToRaster_conversion ("coastOverlap.shp", "HYDROID", "coast.img", "MAXIMUM_COMBINED_LENGTH" ,"NONE", "")
	arcpy.AddMessage("Expanding coastline")
	arcpy.BuildRasterAttributeTable_management ("coast.img", "")
	zone_values = [f.getValue("VALUE") for f in arcpy.SearchCursor("coast.img")]
	coastExpand=Expand("coast.img", 1, zone_values)
	coastExpand.save("coastExpand.img")
	arcpy.AddMessage("Combining coastline with seeds")
	coastSeed=Con(IsNull("comboSeeds.img"), "coastExpand.img", "comboSeeds.img")
	coastSeed.save("finalSeeds.img")
else:
	final.save("finalSeeds.img")


#8 Clipping output by boundaries
arcpy.AddMessage("Clipping seeds to boundary")
arcpy.PolygonToRaster_conversion(inBoundary, 'FID', 'clipBoundary.img', 'MAXIMUM_COMBINED_AREA')
seedClipped=SetNull(IsNull("clipBoundary.img"), "finalSeeds.img")
seedClipped.save(outSeeds)
arcpy.AddMessage("Clipping vertex to boundary")
vertexClipped=SetNull(IsNull("clipBoundary.img"), "finalvertex.img")
vertexClipped.save(outVertex)


