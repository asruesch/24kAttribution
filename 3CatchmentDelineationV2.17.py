import arcpy, math
from arcpy import env
import os.path
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *
env.overwriteOutput = True
env.pyramid="NONE"
env.rasterStatistics="NONE"

def getHydroids(dataset, column):
	rows = arcpy.SearchCursor(dataset,"","",column,"")
	hydroids = []
	for row in rows:
		hydroid = row.getValue(column)
		hydroids.append(hydroid)
	del row, rows
	return hydroids

def demConditioning():
	arcpy.AddMessage("Creating borders for wall-building...")
	maxBuff = 53
	smoothDrop = 167
	sharpDrop = 2000
	arcpy.PolygonToRaster_conversion("tempCatch.shp", 'FID', 'catchRaster.img', 'MAXIMUM_COMBINED_AREA')
	wallMask = Con(IsNull('catchRaster.img'), 0, 1)
	wallMask.save('wallMask.img')
	shrinkCatch = Shrink(wallMask, 1, 1)
	shrinkCatch.save('shrinkCatch.img')
	border = Raster("wallMask.img") - Raster("shrinkCatch.img")
	border.save('border.img')
	borderMask = Raster('wallMask.img') + Raster('border.img')
	borderMask.save('borderMask.img')
	demToBorder = SetNull('borderMask.img', 'demClip.img', "VALUE = 0")
	demToBorder.save("demToBorder.img")
	arcpy.AddMessage("Burning streams...")
	distSeed = Int(EucDistance(Raster("seeds.img")))
	distSeed.save('distSeed.img')
	# AGREE Method
	demSharpBurn = Con(Raster('distSeed.img') == 0, Raster("demToBorder.img") - sharpDrop, "demToBorder.img")
	demSharpBurn.save('demSharpBurn.img')
	demSmoothBurn = Con(Raster('distSeed.img') > 0, Raster('demSharpBurn.img') + (((smoothDrop / maxBuff) * Raster('distSeed.img')) - smoothDrop), 'demSharpBurn.img')
	demSmoothBurn.save('demSmoothBurn.img')
	demBurn = Con(Raster('distSeed.img') > maxBuff, "demToBorder.img", 'demSmoothBurn.img')
	demBurn.save('demBurn.img')
	arcpy.AddMessage("Building walls...")
	demWall = Con(Raster('border.img') == 1, Raster('demBurn.img') + sharpDrop, 'demBurn.img')
	demWall.save('demWall.img')
	demBreach = Con(Raster('distSeed.img') == 0, 'demBurn.img', 'demWall.img')
	demBreach.save('demBreach.img')
	arcpy.AddMessage("Build Columns...")
	demColumn = Con(IsNull('vertexGrid.img'), 'demBreach.img', Raster('demBreach.img') + (sharpDrop * 2))
	demColumn.save('demColumn.img')
	arcpy.AddMessage("Filling DEM...")
	demFill = Fill("demColumn.img", (sharpDrop / 2))
	demFill.save("demFinal.img")
	# delObjs = [wallMask, shrinkCatch, border, borderMask, demToBorder, distSeed, demSharpBurn, demSmoothBurn, demBurn, demWall, demBreach, demColumn]
	# for delObj in delObjs:
		# arcpy.Delete_management(delObj)
	# del delObjs, delObj, demFill


def fixSmallSubshedsAndGreatLakes(huc, outshedWorkspace, greatLakesAnalysis):
	arcpy.AddMessage("Fixing disconnected and tiny watersheds")
	if greatLakesAnalysis:
		# Add original great lakes watersheds back in
		arcpy.RasterToPolygon_conversion("correctedws.img", "correctedws.shp", "NO_SIMPLIFY", "VALUE")
		arcpy.AddField_management("correctedws.shp", "AREA", "FLOAT")
		arcpy.CalculateField_management("correctedws.shp", "AREA", "!SHAPE.AREA@SQUAREMETERS!", "PYTHON")
		arcpy.Select_analysis("correctedws.shp", "correctedws_cleanSmall.shp", '"AREA" > 1000')
		arcpy.PolygonToRaster_conversion("correctedws_cleanSmall.shp", "GRIDCODE", "correctedws.img", "MAXIMUM_COMBINED_AREA")
		arcpy.AddMessage("Fixing Great Lakes Coastal inlets")
		greatLakesWatersheds = Con((Raster("correctedws.img") == 600000001) | (Raster("correctedws.img") == 600124406), "correctedws.img")
		nonGreatLakesHydroids = getHydroids("correctedws.img", "Value")
		if 600000001 in nonGreatLakesHydroids:
			del nonGreatLakesHydroids[nonGreatLakesHydroids.index(600000001)]
		if 600124406 in nonGreatLakesHydroids:
			del nonGreatLakesHydroids[nonGreatLakesHydroids.index(600124406)]
		expandNonGreatLakes = Expand("correctedws.img", 4, nonGreatLakesHydroids)
		greatLakesInserted = Con(IsNull(greatLakesWatersheds), expandNonGreatLakes, greatLakesWatersheds)
		arcpy.BuildRasterAttributeTable_management(greatLakesWatersheds, "Overwrite")
		expand1 = Expand(greatLakesInserted, 4, getHydroids(greatLakesInserted, "Value"))
		arcpy.RasterToPolygon_conversion(expand1, "expandPolygons1.shp", "NO_SIMPLIFY", "VALUE")
		# del nonGreatLakesHydroids, greatLakesWatersheds, expandNonGreatLakes, greatLakesInserted
	else:
		expand1 = Expand("correctedws.img", 4,  getHydroids("correctedws.img", "VALUE"))
		arcpy.RasterToPolygon_conversion(expand1, "expandPolygons1.shp", "NO_SIMPLIFY", "VALUE")
	outshed1 = "outshed1_" + str(huc) + ".shp"
	arcpy.Clip_analysis("expandPolygons1.shp", "tempCatch.shp", outshed1)
	# Select features that:
	# 1) do not interset a seed (eliminates "zippers", and associated extensions)
	# 2) are not a watershed created by the great lakes
	# 3) are less than 1000 m2
	arcpy.RasterToPolygon_conversion("seeds.img", "seedsPolygon.shp", "NO_SIMPLIFY", "VALUE")
	arcpy.MakeFeatureLayer_management(outshed1, "outshed1")
	arcpy.AddField_management("outshed1", "AREA", "FLOAT")
	arcpy.CalculateField_management("outshed1", "AREA", "!SHAPE.AREA@SQUAREMETERS!", "PYTHON")
	arcpy.SelectLayerByLocation_management("outshed1", "INTERSECT", "seedsPolygon.shp", "", "NEW_SELECTION")
	arcpy.SelectLayerByAttribute_management("outshed1", "REMOVE_FROM_SELECTION", '"AREA" <= 1000')
	arcpy.CopyFeatures_management("outshed1", "undesireableWatershedsRemoved.shp")
	arcpy.Delete_management("outshed1")
	arcpy.PolygonToRaster_conversion("undesireableWatershedsRemoved.shp", "GRIDCODE", "undesireableWatershedsRemoved.img", 'MAXIMUM_COMBINED_AREA')
	hydroids = getHydroids("undesireableWatershedsRemoved.shp", "GRIDCODE")
	expand2 = Expand("undesireableWatershedsRemoved.img", 4, hydroids)
	arcpy.RasterToPolygon_conversion(expand2, "expandPolygons2.shp", "NO_SIMPLIFY", "VALUE")
	outshed2 = outshedWorkspace + "/outshed2_" + str(huc) + ".shp"
	arcpy.Clip_analysis("expandPolygons2.shp", "tempCatch.shp", outshed2)
	# del outshed1, hydroids,  expand1, expand2
	return outshed2

def delineateSubsheds():
	inCatch = arcpy.GetParameterAsText(0)
	inCatchID=arcpy.GetParameterAsText(1)
	inSeeds=arcpy.GetParameterAsText(2)
	inVertex = arcpy.GetParameterAsText(3)
	DEM = arcpy.GetParameterAsText(4)
	doDEMConditioning = arcpy.GetParameterAsText(5)
	outWatershed = arcpy.GetParameterAsText(6)
	catchBufferSize = 30
	
	outshedWorkspace = os.path.dirname(outWatershed) + "/tempOutsheds"
	hucWorkspaceDir = os.path.dirname(outWatershed) + "/tempHucOutput"
	
	if not os.path.exists(outshedWorkspace):
		os.mkdir(outshedWorkspace)
	if not os.path.exists(hucWorkspaceDir):
		os.mkdir(hucWorkspaceDir)

	#making a loop of all catchments in a file...
	hucs = getHydroids(inCatch, inCatchID)
	if len(hucs) == 0:
		arcpy.AddError("No Features Available")
		sys.exit("Stopping execution of tool")
	mySheds=[]
	i = 0
	for huc in hucs:
		i = i + 1
		try:
			hucWorkspace = hucWorkspaceDir + "/temp_" + huc
			if not os.path.exists(hucWorkspace):
				os.mkdir(hucWorkspace)
			env.scratchWorkspace = hucWorkspace
			env.workspace = hucWorkspace
			env.outputCoordinateSystem = DEM
			env.cellSize = DEM
			env.snapRaster = DEM
			arcpy.AddMessage(" ")
			arcpy.AddMessage("Processing HUC " + str(i) + " out of " + str(len(hucs)) + " total HUCS (HUC ID " + str(huc) + ")...")
			arcpy.AddMessage("---------------------------------------")
			arcpy.Select_analysis(inCatch, "tempCatch.shp",'"' + inCatchID + '" =' + "'" + str(huc) + "'")
			# buffer catchment unit
			arcpy.AddMessage("Buffering catchments and clipping DEM...")
			catchBuffer = "catchBuffer.shp"
			arcpy.Buffer_analysis("tempCatch.shp", catchBuffer, str(catchBufferSize) + " Meters", "FULL", "", "NONE", "")
			env.extent = catchBuffer
			# clip DEM by buffer
			arcpy.PolygonToRaster_conversion(catchBuffer, 'FID', 'catchBuffer.img', 'MAXIMUM_COMBINED_AREA')
			arcpy.Clip_management(DEM, "#", "demClip.img", catchBuffer, "#", "ClippingGeometry")
			# Set raster environment
			env.extent = "demClip.img"
			arcpy.AddMessage("Selecting seed grid...")
			arcpy.Clip_management(inSeeds, "", "seeds.img", "tempCatch.shp", "","ClippingGeometry")
			# Make sure there are seeds to create watersheds for
			arcpy.BuildRasterAttributeTable_management("seeds.img", "Overwrite")
			seedCount = int(arcpy.GetCount_management("seeds.img").getOutput(0))
			if seedCount == 0:
				outshed = outshedWorkspace + "/outshed2_" + str(huc) + ".shp"
				arcpy.CopyFeatures_management("tempCatch.shp", outshed)
				mySheds.append(outshed)
				env.extent = inCatch
				arcpy.AddMessage(" ")
			else:
				arcpy.Clip_management(inVertex, "", "vertexGrid.img","tempCatch.shp", "","ClippingGeometry")
				##########################################
				if doDEMConditioning == 'true':
					demConditioning()
				##########################################
				seedsMinusConf = Con(IsNull('vertexGrid.img'), "seeds.img")
				seedsMinusConf.save('seedsMinusConf.img')
				# Flow direction
				arcpy.AddMessage('Calculating flow direction...')
				fdr = FlowDirection('demFinal.img', 'NORMAL')
				# Watersheds
				arcpy.AddMessage("Delineating Raster Watersheds...")
				watersheds = Watershed(fdr, "seedsMinusConf.img")
				watersheds.save("watersheds.img")
				# Returning confluence point value back to original stream seed value
				correctedws=Con(IsNull("vertexGrid.img"), "watersheds.img", "seeds.img")
				correctedws.save("correctedws.img")
				# Extract all watershed values for "Expand" procedure
				arcpy.AddMessage("Expanding watersheds to ensure gapless output...")
				arcpy.BuildRasterAttributeTable_management(correctedws, "Overwrite")
				hydroids = getHydroids(correctedws, "Value")
				greatLakesAnalysis = (600000001 in hydroids) or (600124406 in hydroids)
				#################################################
				outshed = fixSmallSubshedsAndGreatLakes(huc, outshedWorkspace, greatLakesAnalysis)
				#################################################
				# Add Catch Id field
				arcpy.AddField_management(outshed, "CATCHID", "TEXT", "", "", "9", "", "", "")
				arcpy.CalculateField_management(outshed, "CATCHID", "[GRIDCODE]")
				fields = arcpy.ListFields(inCatch)
				for field in fields:
					if field.name == inCatchID:
						ftype = field.type
						flen=field.length
						break
				del field, fields
				arcpy.AddField_management(outshed, inCatchID, ftype, "", "", flen, "", "", "")
				value = [f.getValue(inCatchID) for f in arcpy.SearchCursor("tempCatch.shp")]
				catchvalue=value[0]
				arcpy.CalculateField_management(outshed, inCatchID, catchvalue)
				arcpy.AddField_management(outshed, "HUC12", "TEXT", "", "", "12", "", "", "")
				arcpy.CalculateField_management(outshed, "HUC12", str(huc))
				mySheds.append(outshed)
				env.extent = inCatch
				# delObjs = [demFill, seedsMinusConf, fdr, watersheds, correctedws]
				# for delObj in delObjs:
					# arcpy.Delete_management(delObj)
				# del hydroids, seedsMinusConf, fdr, watersheds, correctedws
		except:
			arcpy.AddMessage("Oopsies")
			arcpy.AddMessage(arcpy.GetMessages())
	arcpy.AddMessage("Merging Final Watersheds")
	arcpy.Merge_management (mySheds, "merged.shp", "")
	arcpy.Dissolve_management("merged.shp", outWatershed, ["CATCHID", "HUC12"])
	arcpy.AddMessage(" ")
	# arcpy.Delete_management("merged.shp")
	# fcs = arcpy.ListFeatureClasses()
	# for fc in fcs:
		# arcpy.Delete_management(fc)
	# del fc, fcs
	# remainingFiles = os.listdir(intermediateWorkspace)
	# for remainingFile in remainingFiles:
		# os.remove(remainingFile)
	# del remainingFile, remainingFiles
	# os.rmdir(intermediateWorkspace)

if __name__ == '__main__':
	delineateSubsheds()
