import arcpy, os
import numpy as np
import pandas as pd
from os import path
from arcpy import env
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *
env.overwriteOutput = True
env.pyramid = 'NONE'
env.rasterStatistics = 'NONE'

# Loop through each subshed
# For each subshed, locate the associated line feature in the line coverage
# For the associated line feature in the coverage, find the "to" feature
# If no "to" feature exists, write null value to the "to" subshed feature ID
# Else, check to make sure the "to" feature ID exists in the polygon feature class
# If it does not, it probably means no subshed was created for that feature seed
# If no subshed was created for the feature seed, step down to the next segment in the line coverage and repeat.

# inSubsheds = "C:/TEMP/ripBuff10192012.img"
# inLsns = "C:/Users/ruesca/Documents/GIS/24kAttribution/hydrography/landscapeNetwork/west.mdb;C:/Users/ruesca/Documents/GIS/24kAttribution/hydrography/landscapeNetwork/eastLSN.mdb"
# hydroIdField = 'REACHID'
# huc12Field = 'HUC_12'
# inFdr = "E:/10m_NED/native10mNED/fdr.img"
# connectIsolatedFeatures = 'false'
# outSubsheds =  "C:/TEMP/ripTopology.img"

inSubsheds = arcpy.GetParameterAsText(0)
inLsns = arcpy.GetParameterAsText(1)
hydroIdField = arcpy.GetParameterAsText(2)
# huc12Field = arcpy.GetParameterAsText(3)
connectIsolatedFeatures = arcpy.GetParameterAsText(3)
inFdr = arcpy.GetParameterAsText(4)
outSubsheds = arcpy.GetParameterAsText(5)

inLsns = inLsns.split(';')

tempFolder = os.path.dirname(inSubsheds) + "/tempTopology"
if not os.path.exists(tempFolder):
	os.mkdir(tempFolder)
env.workspace = tempFolder
env.scratchWorkspace = tempFolder


def getColVals(dataset, column):
	rows = arcpy.SearchCursor(dataset,"","",column,"")
	hydroids = []
	for row in rows:
		hydroid = row.getValue(column)
		hydroids.append(hydroid)
	del row, rows
	return hydroids

arcpy.AddMessage("Pulling topology from landscape networks")

if len(inLsns) > 1:
	i = 0
	maxFeat = 0
	for inLsn in inLsns:
		i = i + 1
		rows = arcpy.SearchCursor(inLsn + "/edges", "", "", hydroIdField + "; rid")
		hydroIds = []
		rids = []
		for row in rows:
			hydroId= row.getValue(hydroIdField)
			rid = row.rid
			hydroIds.append(hydroId)
			rids.append(rid)
		del row, rows, hydroId, rid
		rows = arcpy.SearchCursor(inLsn + "/relationships", "", "", "fromfeat; tofeat")
		fromfeats = []
		tofeats = []
		for row in rows:
			fromfeat = row.fromfeat
			if fromfeat in rids:
				tofeat = row.tofeat
				fromfeats.append(fromfeat)
				tofeats.append(tofeat)
		del row, rows, fromfeat, tofeat
		hydroIds = np.array(hydroIds)
		rids = np.array(rids) + maxFeat
		tofeats = np.array(tofeats) + maxFeat
		fromfeats = np.array(fromfeats) + maxFeat
		#####################################
		edgeTable = np.zeros((len(hydroIds),), dtype=[('HYDROID', 'i4'),('RID', 'i4')])
		edgeTable['HYDROID'] = hydroIds
		edgeTable['RID'] = rids
		relationshipTable = np.zeros((len(fromfeats),), dtype=[('RID', 'i4'),('TOFEAT', 'i4')])
		relationshipTable['RID'] = fromfeats
		relationshipTable['TOFEAT'] = tofeats
		if i == 1:
			edgeDta = np.array(edgeTable)
			relationshipDta = np.array(relationshipTable)
		else:
			edgeDta = np.append(edgeDta, edgeTable, axis = 0)
			relationshipDta = np.append(relationshipDta, relationshipTable, axis = 0)
		maxFeat = np.amax(rids) + maxFeat + 1
		del hydroIds, rids, tofeats, fromfeats, edgeTable, relationshipTable
else:
	rows = arcpy.SearchCursor(inLsns[0] + "/edges", "", "", hydroIdField + "; rid")
	hydroIds = []
	rids = []
	for row in rows:
		hydroId= row.getValue(hydroIdField)
		rid = row.rid
		hydroIds.append(hydroId)
		rids.append(rid)
	del row, rows, hydroId, rid
	rows = arcpy.SearchCursor(inLsns[0] + "/relationships", "", "", "fromfeat; tofeat")
	fromfeats = []
	tofeats = []
	for row in rows:
		fromfeat = row.fromfeat
		if fromfeat in rids:
			tofeat = row.tofeat
			fromfeats.append(fromfeat)
			tofeats.append(tofeat)
	del row, rows, fromfeat, tofeat
	hydroIds = np.array(hydroIds)
	rids = np.array(rids)
	tofeats = np.array(tofeats)
	fromfeats = np.array(fromfeats)
	edgeDta = np.zeros((len(hydroIds),), dtype=[('HYDROID', 'i4'),('RID', 'i4')])
	edgeDta['HYDROID'] = hydroIds
	edgeDta['RID'] = rids
	relationshipDta = np.zeros((len(fromfeats),), dtype=[('RID', 'i4'),('TOFEAT', 'i4')])
	relationshipDta['RID'] = fromfeats
	relationshipDta['TOFEAT'] = tofeats
	del hydroIds, rids, tofeats, fromfeats

arcpy.AddMessage("Compiling network topology across landscape network(s)")
edgeDta = pd.DataFrame(edgeDta)
relationshipDta = pd.DataFrame(relationshipDta)
edgeJoin = pd.merge(edgeDta, relationshipDta, how='left', on='RID')
edgeJoin.ix[edgeJoin['TOFEAT'].isnull(), 'TOFEAT'] = 999999
edgeJoin['TOFEAT'] = edgeJoin['TOFEAT'].map(int)
del edgeDta, relationshipDta

arcpy.AddMessage("Preparing zone data")
inType = arcpy.Describe(inSubsheds).datasetType
if inType == u'RasterDataset':
	if not Raster(inSubsheds).hasRAT:
		arcpy.BuildRasterAttributeTable_management(inSubsheds)
	fields = arcpy.ListFields(inSubsheds)
	for field in fields:
		if not field.name == 'CATCHID':
			fieldExists = False
		else:
			fieldExists = True
			break
	if not fieldExists:
		arcpy.AddField_management(inSubsheds, "CATCHID", "LONG", "", "", 9, "", "", "")
	rows = arcpy.UpdateCursor(inSubsheds)
	for row in rows:
		row.CATCHID = row.Value
		rows.updateRow(row)
	del row, rows
subshedIds = getColVals(inSubsheds, "CATCHID")
subshedIds = map(int, subshedIds)
subshedIds = pd.Series(subshedIds)

arcpy.AddMessage("Populating 'TO' Field")
print "Populating \"TO\" Field"

toHydroids = pd.Series(np.zeros(len(subshedIds)))
j = -1

arcpy.SetProgressor("step", "", 0, len(toHydroids), 1)
arcpy.AddMessage("Conflating landscape network topology to subsheds")
for subshedId in subshedIds:
	j = j + 1
	print subshedId
	arcpy.SetProgressorLabel("Hydroid: " + str(subshedId))
	# Get "to" data for all reaches associate with subshedId
	toDta = edgeJoin.ix[edgeJoin['HYDROID'] == subshedId]
	# Does subshedId go "to" anything?
	if toDta.shape[0] > 0:
		flagTransition = False
		i = 0
		while flagTransition == False:
			i = i + 1
			# What is the rid of the feature that goes "to" something other than itself
			tofeat = toDta.ix[-toDta['TOFEAT'].isin(toDta['RID']), 'TOFEAT']
			if tofeat.shape[0] > 1:
				tofeat = tofeat[tofeat.index[0]]
				arcpy.AddWarning("REACHID " + str(subshedId) + " has multiple 'to' features")
				toHydroid = 999999
				break
			toHydroid = edgeJoin.ix[edgeJoin['RID'].isin(tofeat), 'HYDROID']
			# Are we already at a terminal feature?
			if toHydroid == 999999:
				break
			if toHydroid.shape[0] == 0:
				toHydroid = 999999
				break
			# Is the Hydroid a member of subshedIds (i.e., was a watershed created for it?)
			if toHydroid.isin(subshedIds):
				flagTransition = True
			if i > 30:
				arcpy.AddWarning("RID " + str(tofeat) + " caused possible infinite loop. Check topology")
			# Step downstream and repeat
			toDta = edgeJoin.ix[edgeJoin['HYDROID'] == int(toHydroid)]
	else:
		toHydroid = 999999
	toHydroids[j] = toHydroid
	arcpy.SetProgressorPosition()
arcpy.ResetProgressor()
del edgeJoin, subshedId, subshedIds, toDta, flagTransition, tofeat, toHydroid


arcpy.AddMessage("Creating topologically populated output")
if inType == u'RasterDataset':
	arcpy.CopyRaster_management(inSubsheds, outSubsheds)
else:
	arcpy.CopyFeatures_management(inSubsheds, outSubsheds)
arcpy.AddField_management(outSubsheds, "TOCATCHID", "LONG", "", "", 9, "", "", "")
rows = arcpy.UpdateCursor(outSubsheds)
i = -1
for row in rows:
	i = i + 1
	row.TOCATCHID = int(toHydroids[i])
	rows.updateRow(row)
del row, rows, toHydroids

#############################################
#############################################
##
##	Connect Isolated Lakes
##
#############################################
##############################################
if connectIsolatedFeatures == 'true':
	arcpy.AddMessage(" ")
	arcpy.AddMessage("Connecting Isolated Features")
	arcpy.AddMessage(" ")
	print "Connecting Isolated Features"

	bufferDistance = 10 * math.sqrt(2)

	arcpy.MakeFeatureLayer_management(outSubsheds, "outSubsheds")
	arcpy.SelectLayerByAttribute_management("outSubsheds", "NEW_SELECTION", "TOCATCHID = 999999")
	isolatedSubsheds = getColVals("outSubsheds", "CATCHID")
	arcpy.SelectLayerByAttribute_management("outSubsheds", "CLEAR_SELECTION")

	##################################
	## Comment out when finished testing
	# isolatedSubsheds = isolatedSubsheds[:20]
	##################################

	for isolatedSubshed in isolatedSubsheds:
		print "   " + str(isolatedSubshed)
		## Select bordering polygons
		# print "		selecting bordering polygons"
		arcpy.SelectLayerByAttribute_management("outSubsheds", "NEW_SELECTION", '"CATCHID" = \'' + str(isolatedSubshed) + "'")
		arcpy.env.extent = "outSubsheds"
		arcpy.CopyFeatures_management("outSubsheds", "isolatedSubshed.shp")
		arcpy.SelectLayerByLocation_management("outSubsheds", "BOUNDARY_TOUCHES", "isolatedSubshed.shp", "#", "ADD_TO_SELECTION")
		# arcpy.Buffer_analysis("outSubsheds", "subshedsAndBuffer.shp", bufferDistance, "", "", "ALL")

		arcpy.SelectLayerByAttribute_management("outSubsheds", "REMOVE_FROM_SELECTION", '"CATCHID" = \'' + str(isolatedSubshed) + "'")
		arcpy.MakeFeatureLayer_management("outSubsheds", "borderingPolygons")
		arcpy.SelectLayerByAttribute_management("outsubsheds", "CLEAR_SELECTION")
		##########################################
		## Create buffer on target isolated subshed
		# print "		create watershed buffer"
		arcpy.SelectLayerByAttribute_management("outSubsheds", "NEW_SELECTION", '"CATCHID" = \'' + str(isolatedSubshed) + "'")
		arcpy.Buffer_analysis("outSubsheds", "isolatedSubshedBuffer.shp", bufferDistance, "OUTSIDE_ONLY", "", "ALL")
		##########################################
		## Clip flow direction and calculate flow accumulation
		# print "		clip flow direction raster"
		arcpy.Clip_management(inFdr, "", "fdrClipped.img", "isolatedSubshedBuffer.shp")
		# print "		calculate flow accumulation"
		arcpy.env.extent = "fdrClipped.img"
		fac = FlowAccumulation("fdrClipped.img", "", "INTEGER")
		fac.save("fac.img")
		del fac
		##########################################
		## Rasterize buffer
		env.extent = "fac.img"
		env.snapRaster = "fac.img"
		env.cellSize = "fac.img"
		# print "		rasterize buffer"
		arcpy.PolygonToRaster_conversion("isolatedSubshedBuffer.shp", "FID", "rasterMask.img", "CELL_CENTER", "#", "fac.img")
		#########################################
		# print "		convert max cell to point"
		yMax = float(arcpy.GetRasterProperties_management("fac.img", "TOP").getOutput(0))
		xMin = float(arcpy.GetRasterProperties_management("fac.img", "LEFT").getOutput(0))
		rasterMaskArray = arcpy.RasterToNumPyArray("rasterMask.img")
		facArray = arcpy.RasterToNumPyArray("fac.img")
		maxAcc = np.amax(facArray[rasterMaskArray <> 255])
		outPx = np.array(np.where((facArray == maxAcc) & (rasterMaskArray <> 255)))
		yCoord = float(yMax) - (outPx[0,:] * 10.0) - 5.0
		xCoord = float(xMin) + (outPx[1,:] * 10.0) + 5.0
		arcpy.CreateFeatureclass_management(tempFolder, "maxCells.shp", "Point", "isolatedSubshedBuffer.shp")
		cur = arcpy.InsertCursor("maxCells.shp")
		for i in np.arange(len(xCoord)):
			point = arcpy.Point(xCoord[i], yCoord[i])
			feat = cur.newRow()
			feat.shape = point
			cur.insertRow(feat)
		del cur, yMax, xMin, rasterMaskArray, facArray, outPx, yCoord, xCoord, point, feat
		# print "		intersect point with neighboring polygon"
		arcpy.SelectLayerByLocation_management('borderingPolygons', 'CONTAINS', "maxCells.shp", "#", "NEW_SELECTION")
		##########################################
		## get CATCHID values; build TO/FROM topology
		# print "		build polygon-to-polygon topology"
		numberOfToPolygons = int(arcpy.GetCount_management("borderingPolygons").getOutput(0))
		if numberOfToPolygons > 0:
			flagMultTos = False
			catchids = list()
			rows = arcpy.SearchCursor("borderingPolygons")
			for row in rows:
				catchid = row.getValue('CATCHID')
				catchids.append(catchid)
			del rows, row
		else:
			catchids = [999999]
		if (len(catchids) > 1):
			flagMultTos = True
		rows = arcpy.UpdateCursor(outSubsheds, '"CATCHID" = \'' + str(isolatedSubshed) + "'")
		for row in rows:
			row.TOCATCHID = catchids[0]
			rows.updateRow(row)
		del row, rows, catchids, numberOfToPolygons
		##########################################
		## Clean up
		# print "		clean up"
		arcpy.env.extent = inFdr
		arcpy.env.snapRaster = inFdr
		arcpy.env.cellSize = inFdr
		try:
			arcpy.Delete_management("fac.img")
		except:
			arcpy.AddMessage("delete fail")
		delDatasets = arcpy.ListDatasets(env.scratchWorkspace)
		for delDataset in delDatasets:
			try:
				arcpy.Delete_management(delDataset)
			except:
				arcpy.AddMessage("delete fail")
		del delDatasets
