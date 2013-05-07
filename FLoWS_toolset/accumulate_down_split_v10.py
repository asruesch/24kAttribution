# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~  ACCUMULATE VALUE DOWN STREAM   ~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# The purpose of this script is to accumulate a numeric value down
# a GeoNetwork.  This means that the network that the value is 
# accumulated down must have a relationship table that hold edge 
# to edge relationship sorted in order of occurance down stream

# ~~~~~~~~~~~~~~~~  Contact Information ~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~ Dave Theobald (Natural Resources Ecology Lab - NREL)  ~~~~~
# ~~~	 Colorado State University, Fort Collins CO		 ~~~~~
# ~~~	 e-mail: davet@nrel.colostate.edu				   ~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create by: John Norman 9/7/04
# Last Modified: 9/9/04

# Create the geoprocessor

import arcpy, sys, string, os, re, time, win32com.client, win32api
from time import *
from arcpy import env
env.overwriteOutput = True

# Create the Geoprocessor object
# arcpy = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
# arcpy = arcgisscripting.create()
arcpy.AddMessage("starting script")
conn = win32com.client.Dispatch(r'ADODB.Connection')
arcpy.AddMessage("connection opened")

try:
	arcpy.AddMessage("reading parameters")
	InputFC = arcpy.GetParameterAsText[1]											  # Input Feature Class
	OutField = arcpy.GetParameterAsText[2]
	AccField = arcpy.GetParameterAsText[3]											  # field to accumulate on
	SplitWeightField = arcpy.GetParameterAsText[4]
	arcpy.AddMessage("parameters read")
	Path = arcpy.Describe(InputFC).Path	# Get the full path of the featureclass this includes PGDB name
	FeatureclassPath = Path
	PGDBName = os.path.basename(Path)							   # Get the PGDB full name from Featureclasspath
	FullFeatureclassPath = Path
	arcpy.AddMessage(Path)


	env.workspace = Path											#set work space = to featureclass path
	DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + Path
	conn.Open(DSN)

	FeatureclassName = arcpy.Describe(InputFC).Name
	RelTableName = "relationships"
	# AccField = "shape_length"

	# look and see if the table valence exists, if it does then delete it	
	tbs = arcpy.ListTables(RelTableName)
	# tb = tbs.next()
	arcpy.AddMessage("starting accumulation loop")
	if len(tbs) > 0: # IF ReltableName exists then 
		rs = win32com.client.Dispatch(r'ADODB.Recordset')
		rs1 = win32com.client.Dispatch(r'ADODB.Recordset')
		# rs_name = RelTableName
		if SplitWeightField <> "#":
			querystring = "SELECT First(relationships.OBJECTID) AS FirstOfOBJECTID, relationships.fromfeat, Sum(" + FeatureclassName + "." + AccField + ") AS from_value, relationships.tofeat, Sum(" + FeatureclassName + "_1." + AccField + ") AS to_value, Min(" + FeatureclassName + "." + SplitWeightField + ") AS split FROM (relationships LEFT JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid) LEFT JOIN " + FeatureclassName + " AS " + FeatureclassName + "_1 ON relationships.tofeat = " + FeatureclassName + "_1.rid GROUP BY relationships.fromfeat, relationships.tofeat ORDER BY First(relationships.OBJECTID);"
		else:
			querystring = "SELECT First(relationships.OBJECTID) AS FirstOfOBJECTID, relationships.fromfeat, Sum(" + FeatureclassName + "." + AccField + ") AS from_value, relationships.tofeat, Sum(" + FeatureclassName + "_1." + AccField + ") AS to_value FROM (relationships LEFT JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid) LEFT JOIN " + FeatureclassName + " AS " + FeatureclassName + "_1 ON relationships.tofeat = " + FeatureclassName + "_1.rid GROUP BY relationships.fromfeat, relationships.tofeat ORDER BY First(relationships.OBJECTID);"
		#arcpy.AddMessage(querystring)
		rs.Open(querystring, conn, 1) 
		rs.MoveFirst
		count = 0
		# loop through the recordset and accumulate value down stream.  This can be done because the table is sorted downstream
		FeatureList = [] # this list holds feature IDs that have been add or accumulated
		AccumulateValueList = [] # this list holds add or accumulated feature values
		arcpy.AddMessage(" ")
		arcpy.AddMessage("Accumulating Downstream....")
		arcpy.AddMessage(" ")
		splitweight = 1
		while not rs.EOF:
			if SplitWeightField <> "#":
				splitweight = rs.Fields.Item("split").Value
				if not splitweight:
					if splitweight <> 0:splitweight = 1
					
			fromfeat = rs.Fields.Item("fromfeat").Value
			tofeat = rs.Fields.Item("tofeat").Value
			fromvalue = rs.Fields.Item("from_value").Value

			#arcpy.AddMessage(str(fromfeat) + " " + str(fromvalue))
			
			if not fromvalue:
				fromvalue = 0
			tovalue = rs.Fields.Item("to_value").Value
			if not tovalue:
				tovalue = 0
			toexists = tofeat in FeatureList
			fromexists = fromfeat in FeatureList
			if fromexists == 0: # if fromfeature not in list add it and add its weight value to accumulate list
				FeatureList.append(fromfeat)
				AccumulateValueList.append(fromvalue)
			if toexists == 1: # if tofeature exists in list accumulate it
				ind = FeatureList.index(tofeat)
				if fromexists == 1: # if fromfeature and tofeature exist in list add fromfeature's list value to to node value
					ind2 = FeatureList.index(fromfeat)
					AccumulateValueList[ind] = (float(AccumulateValueList[ind2] * splitweight) + AccumulateValueList[ind])
				else:
					AccumulateValueList[ind] = AccumulateValueList[ind] + float(fromvalue * splitweight)
			else:
				FeatureList.append(tofeat)
				if fromexists == 1:
					ind2 = FeatureList.index(fromfeat)
					AccumulateValueList.append(float(AccumulateValueList[ind2] * splitweight) + tovalue)
				else:
					AccumulateValueList.append(tovalue + float(fromvalue * splitweight))
			rs.MoveNext()
		rs.Close()
		rs = "Nothing"
		#time.sleep(4.0)
		conn.Close()

		arcpy.AddMessage("test")
		if len(arcpy.ListFields(FeatureclassName, OutField)) <> 0:
			arcpy.AddMessage("Populating Field " + OutField + "...")
		else:
			arcpy.AddMessage("Populating Field " + OutField + "....")
			arcpy.AddField_management(FeatureclassName, OutField, "double")
			arcpy.AddMessage("field added")
		string = AccField + " IS NOT NULL"
		arcpy.AddMessage("Selecting")
		arcpy.AddMessage(FeatureclassName)
		arcpy.MakeFeatureLayer_management(FeatureclassName, "lyr")
		arcpy.SelectLayerByAttribute_management("lyr", "ADD_TO_SELECTION", string)
		calcfield =  "[" + AccField + "]"
		arcpy.AddMessage("Calculating Field")
		arcpy.CalculateField_management("lyr", OutField, calcfield)
		arcpy.SelectLayerByAttribute_management("lyr", "CLEAR_SELECTION")
		arcpy.CopyFeatures_management("lyr", FeatureclassName + OutField)
		arcpy.Delete_management("lyr")
		#arcpy.CalculateField(FeatureclassName, OutField, "0")
		arcpy.AddMessage("Field Calculated")
			
		Rows = arcpy.UpdateCursor(FeatureclassName)
		Row = Rows.Next()
		while Row:
			rid = Row.rid
			exists = rid in FeatureList
			if exists > 0:
				ind = FeatureList.index(rid)
				Row.SetValue(OutField, AccumulateValueList[ind])
				#arcpy.AddMessage(str(rid) + "   " + str(AccumulateValueList[ind]))
				del FeatureList[ind]
				del AccumulateValueList[ind]
				Rows.UpdateRow(Row)
			Row = Rows.Next()
		arcpy.AddMessage("  ")
		arcpy.AddMessage("  ")
		arcpy.AddWarning("Finished Accumulate Values Downstream Script")
		arcpy.AddMessage("  ")
		arcpy.AddMessage("  ")
		arcpy.AddMessage("  ")
	else:
		arcpy.AddMessage("Relationship table doesn't exist")
		

except:
	print arcpy.GetMessages(0)
	print conn.GetMessages()
	
	