import arcpy, sys, os.path
import numpy as np
import pandas as pd

zoneTopologyFile = arcpy.GetParameterAsText(0)
zoneSubsetField = arcpy.GetParameterAsText(1)
attributeTableFile = arcpy.GetParameterAsText(2)
indCol = arcpy.GetParameterAsText(3)
areaCol = arcpy.GetParameterAsText(4)
stat = arcpy.GetParameterAsText(5)
outputTable = arcpy.GetParameterAsText(6)
circTopolTable = arcpy.GetParameterAsText(7)

# Change to "True" if area-weighted averages should be based on polygon areas as opposed to cellCounts
polygonBasedArea = False
if stat == 'area-weighted average':
	if areaCol == '':
		polygonBasedArea = True
	else:
		polygonBasedArea = False

def wavg(data, weights):
	floatData = pd.Series(map(float, data))
	floatWeights = pd.Series(map(float, weights))
	return (floatData * floatWeights).sum() / floatWeights.sum()

def traceAttribution(zoneTopologyFile, attributeTableFile, indCol, stat, outputTable):
	arcpy.AddMessage("Reading zone topology table...")
	if polygonBasedArea == True:
		shapeCol = arcpy.Describe(zoneTopologyFile).shapeFieldName
	rows = arcpy.SearchCursor(zoneTopologyFile)
	hydroids = []
	tohydroids = []
	if stat == 'area-weighted average':
		areas = []
	if zoneSubsetField <> '':
		subset = []
	for row in rows:
		hydroid = row.getValue("CATCHID")
		tohydroid = row.getValue("TOCATCHID")
		hydroids.append(hydroid)
		tohydroids.append(tohydroid)
		if (stat == 'area-weighted average') and (polygonBasedArea == True):
			area = (row.getValue(shapeCol)).area
			areas.append(area)
		if zoneSubsetField <> '':
			subsetVal = row.getValue(zoneSubsetField)
			subset.append(subsetVal)
	del row, rows, hydroid, tohydroid
	if (stat == 'area-weighted average') and (polygonBasedArea == True):
		del area
	if zoneSubsetField <> '':
		del subsetVal
	hydroids = map(int, hydroids)
	hydroids = map(str, hydroids)
	tohydroids = map(int, tohydroids)
	tohydroids = map(str, tohydroids)
	topologyTable = pd.DataFrame(tohydroids, index=hydroids, columns = ['TOHYDROID'])
	if zoneSubsetField <> '':
		subset = pd.Series(subset)
		hydroids = pd.Series(topologyTable.index).ix[subset == 1]
		hydroids = map(str, hydroids)
	if (stat == 'area-weighted average') and (polygonBasedArea == True):
		areas = map(float, areas)
		topologyTable['AREA'] = areas
		topologyTable['AREA'] = topologyTable['AREA'] / 1000**2
	arcpy.AddMessage("Reading attribute table...")
	attributeTableReader = pd.read_csv(attributeTableFile, na_values='NA', index_col=indCol, chunksize=10000)
	i = -1
	for chunk in attributeTableReader:
		i += 1
		if i == 0:
			attributeTable = pd.DataFrame.copy(chunk)
		else:
			attributeTable = pd.concat([attributeTable, chunk], axis=0)
	del attributeTableReader
	attributeTable.index = map(int, attributeTable.index)
	attributeTable.index = map(str, attributeTable.index)
	if (stat == 'area-weighted average') and (polygonBasedArea == False):
		areas = pd.DataFrame(attributeTable[areaCol].map(float), columns = ['AREA'])
		topologyTable = pd.merge(topologyTable, areas, left_index=True, right_index=True)
	dtaCols = attributeTable.columns
	newCols = pd.Index("Tr" + pd.Series(dtaCols))
	statMat = np.empty((len(hydroids), attributeTable.shape[1]), dtype='float')
	statMat[:] = np.NAN
	statTable = pd.DataFrame(statMat)
	statTable.columns = dtaCols
	del statMat

	circTopol = pd.Series([])

	n = len(hydroids)
	i = -1
	arcpy.SetProgressor("step", "", 0, n, 1)
	arcpy.AddMessage("Accumulating upstream zone attributes...")
	for hydroid in hydroids:
		i += 1
		arcpy.SetProgressorLabel("hydroid: " + str(hydroid))
		upstrIds = pd.Series([hydroid])
		tos = pd.Series([hydroid])
		end = False
		j = 0
		while end == False:
			j += 1
			froms = topologyTable.index[topologyTable['TOHYDROID'].isin(tos)]
			if len(froms) > 0:
				upstrIds = upstrIds.append(pd.Series(froms))
			else:
				end = True
			# step up one tier on network hierarchy
			tos = froms
			if j > 1000:
				arcpy.AddWarning("Hydroid " + str(hydroid) + " has circular topology, skipping")
				if circTopolTable <> '':
					circTopol = circTopol.append(pd.Series([hydroid]))
				break
		upstrIds = pd.Series(upstrIds.unique())
		upstrDta = attributeTable.ix[upstrIds]
		if stat == 'area-weighted average':
			upstrAreas = topologyTable.ix[upstrIds, 'AREA']
			means = upstrDta.apply(wavg, axis = 0, weights = upstrAreas)
			statTable.ix[i] = means
			del means, upstrAreas
		if stat == 'sum':
			sums = upstrDta.sum(axis = 0)
			statTable.ix[i] = sums
			del sums
		del upstrIds, tos, end, froms, upstrDta
		arcpy.SetProgressorPosition()
	arcpy.ResetProgressor()
	statConcat = pd.DataFrame(hydroids)
	statConcat.columns = pd.Index(['CATCHID'])
	statConcat[newCols] = statTable
	arcpy.AddMessage("Writing trace attribute table...")
	statConcat.to_csv(outputTable, index=False, na_rep='NA')
	if circTopolTable <> '':
		if len(circTopol) > 0:
			circTopol = pd.DataFrame(circTopol)
			circTopol.columns = pd.Index(['CATCHID'])
			circTopol.to_csv(circTopolTable, index=False)
		else:
			arcpy.AddMessage("No circular topologies!")

if __name__ == "__main__":
	traceAttribution(zoneTopologyFile, attributeTableFile, indCol, stat, outputTable)