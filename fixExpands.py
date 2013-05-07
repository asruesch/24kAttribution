#designed as a loop through all HUC12s that need to be fixed but I am pretty sure it will crash
#b/c of the cost allocation; you can run it as a batch process
#also, need to add GRIDCODE field to delineated watersheds that is an integer field b/c cannot create correct raster sheds with string catch ID field

import arcpy
import os.path
from arcpy import env
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *
env.overwriteOutput = True

inCatch = arcpy.GetParameterAsText(0)
inCatchID=arcpy.GetParameterAsText(1)
delineations=arcpy.GetParameterAsText(2)
DEM = arcpy.GetParameterAsText(3)
outFinalSheds=arcpy.GetParameterAsText(4)


#huc = r'F:\Menuz\delineation\fixExpands\HUC1.shp'
#hucID=
#delineations=r'F:\Menuz\delineation\stateComplete10022012.shp'
#DEM = r'F:\DEM\raw_prj.img'
#outshed=r'F:\Menuz\delineation\fixExpands\outsheds\HUC1out.shp'



#################
outshedWorkspace = os.path.dirname(outFinalSheds) + "/tempOutsheds"
hucWorkspaceDir = os.path.dirname(outFinalSheds) + "/tempOutput"
if not os.path.exists(hucWorkspaceDir):
    os.mkdir(hucWorkspaceDir)
if not os.path.exists(outshedWorkspace):
    os.mkdir(outshedWorkspace)

def getHydroids(dataset, column):
    rows = arcpy.SearchCursor(dataset,"","",column,"")
    hydroids = []
    for row in rows:
        hydroid = row.getValue(column)
        hydroids.append(hydroid)
    del row, rows
    return hydroids


hucs = getHydroids(inCatch, inCatchID)
if len(hucs) == 0:
    arcpy.AddError("No Features Available")
    sys.exit("Stopping execution of tool")
shedList=[]

for huc in hucs:
	hucWorkspace = hucWorkspaceDir + "/temp_" + huc
	if not os.path.exists(hucWorkspace):
		os.mkdir(hucWorkspace)
	outshed = outshedWorkspace + "/outshed_" + str(huc) + ".shp"
	shedList.append(outshed)
	env.scratchWorkspace = hucWorkspace
	env.workspace = hucWorkspace
	env.outputCoordinateSystem = DEM
	env.cellSize = DEM
	env.snapRaster = DEM
	arcpy.AddMessage(" ")
	arcpy.AddMessage("---------------------------------------")
	arcpy.Select_analysis(inCatch, "tempCatch.shp",'"' + inCatchID + '" =' + "'" + str(huc) + "'")
	arcpy.Buffer_analysis("tempCatch.shp", "catchBuffer.shp", "20 Meters", "FULL", "", "NONE")
	env.extent="catchBuffer.shp"
	arcpy.AddMessage("Selecting watersheds...")
	arcpy.MakeFeatureLayer_management("tempCatch.shp", "huc")
	arcpy.MakeFeatureLayer_management(delineations, "sheds")
	arcpy.SelectLayerByLocation_management("sheds", "WITHIN", "huc", "", "NEW_SELECTION")
	arcpy.CopyFeatures_management("sheds", "hucSheds.shp")
	arcpy.AddField_management("hucSheds.shp", "GRIDCODE", "LONG", "12")
	arcpy.CalculateField_management("hucSheds.shp", "GRIDCODE", "[CATCHID]")
	arcpy.PolygonToRaster_conversion("hucSheds.shp", "GRIDCODE", "shedToAllocate.img", 'MAXIMUM_COMBINED_AREA')
	arcpy.AddMessage("Allocating to fill in watersheds...")
	allocatedSheds=EucAllocation("shedToAllocate.img")
	allocatedSheds.save("allocatedSheds.img")
	arcpy.RasterToPolygon_conversion("allocatedSheds.img", "allocatedSheds.shp", "NO_SIMPLIFY", "VALUE")
	arcpy.AddMessage("Clipping watersheds...")
	arcpy.Clip_analysis("allocatedSheds.shp", "tempCatch.shp", outshed)
	arcpy.AddMessage("Filling in watershed data...")
	arcpy.AddField_management(outshed, "CATCHID", "TEXT", "", "", "9", "", "", "")
	arcpy.CalculateField_management(outshed, "CATCHID", "[GRIDCODE]")
	arcpy.DeleteField_management(outshed, ["GRIDCODE"])
	arcpy.DeleteField_management(outshed, ["ID"])
	arcpy.AddField_management(outshed, "HUC12", "TEXT", "", "", "12", "", "", "")
	arcpy.CalculateField_management(outshed, "HUC12", str(huc))


env.extent=delineations
arcpy.MakeFeatureLayer_management(delineations, "sheds")
arcpy.MakeFeatureLayer_management(inCatch, "inCatch")
arcpy.SelectLayerByLocation_management("sheds", "WITHIN", "inCatch", "","NEW_SELECTION")
arcpy.SelectLayerByAttribute_management("sheds", "SWITCH_SELECTION")
arcpy.CopyFeatures_management("sheds", "okaysheds.shp")
shedList.append("okaysheds.shp")
arcpy.Merge_management(shedList, outFinalSheds)