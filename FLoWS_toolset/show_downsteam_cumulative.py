# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Show upstream selection based on selected features  ~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Based on a selection set this tool will show all upstream features

# ~~~~~~~~~~~~~~~~  Contact Information ~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~ Dave Theobald (Natural Resources Ecology Lab - NREL)  ~~~~~
# ~~~     Colorado State University, Fort Collins CO         ~~~~~
# ~~~     e-mail: davet@nrel.colostate.edu                   ~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Created by: John Norman 9/7/04
# Last Modified: 9/9/04

# Create the geoprocessor

import arcgisscripting, sys, string, os, re, time, win32com.client, win32api
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()

conn = win32com.client.Dispatch(r'ADODB.Connection')
# Get ArcObjects Interfaces
#pDoc = win32com.client.Dispatch("IMxDocument.ThisDocument")
def GetUpstreamFeatures(conn, EdgeList, EdgeWeightList, FeatureclassName, WeightItem, id, weightValue):
    rs = win32com.client.Dispatch(r'ADODB.Recordset')
    querystring = "SELECT relationships.fromfeat, relationships.tofeat, " + FeatureclassName + "." + WeightField + " AS weight FROM relationships INNER JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid WHERE (((relationships.tofeat)=" + str(id) + "));"
    #gp.AddMessage(querystring)
    rs.Cursorlocation = 3
    rs.Open(querystring, conn, 1, 3)
    rs.MoveFirst
    if rs.RecordCount > 0:
        while not rs.EOF:
            exists = rs.Fields.Item("fromfeat").Value in EdgeList
            if exists == 0:
                if (weightValue - rs.Fields.Item("weight").Value) >= 0:
                    #weightValue = weightValue - rs.Fields.Item("weight").Value
                    EdgeList.append(rs.Fields.Item("fromfeat").Value)
                    EdgeWeightList.append(weightValue - rs.Fields.Item("weight").Value)
            rs.MoveNext()
    rs = "Nothing"
    return 1

def GoUpstream(conn, upstreamList, upstreamWeightList, startList, id, weightValue, FeatureclassName, WeightItem):
    EdgeList = []
    EdgeWeightList = []
    EdgeList.append(id)
    EdgeWeightList.append(weightValue)
    index = 0
    for rid in EdgeList:
        exists = rid in upstreamList
        if exists == 0:
            exists = rid in startList
            if exists == 0:
                upstreamList.append(rid)
                upstreamWeightList.append(EdgeWeightList[index])
                dummy = GetUpstreamFeatures(conn, EdgeList, EdgeWeightList, FeatureclassName, WeightItem, rid, EdgeWeightList[index])
        index = index + 1
    EdgeList = []
    EdgeWeightList = []
    return 1

def GetDownstreamFeatures(conn, ridList, weightList, id, weightValue, FeatureclassName, WeightField):
    rs = win32com.client.Dispatch(r'ADODB.Recordset')
    querystring = "SELECT relationships.fromfeat, relationships.tofeat, " + FeatureclassName + "." + WeightField + " AS weight FROM relationships INNER JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid WHERE (((relationships.fromfeat)=" + str(rid) + "));"
    rs.Cursorlocation = 3
    rs.Open(querystring, conn, 1, 3)
    rs.MoveFirst
    if rs.RecordCount > 0:
        while not rs.EOF:
            exists = rs.Fields.Item("tofeat").Value in ridList
            if exists == 0:
                if (weightValue - rs.Fields.Item("weight").Value) >= 0:
                    weightList.append(weightValue - rs.Fields.Item("weight").Value)
                    ridList.append(rs.Fields.Item("tofeat").Value)
            rs.MoveNext()
    rs = "Nothing"
    return 1

if __name__ == "__main__":

    InputFC = sys.argv[1]    # Input Feature Class
    WeightField = sys.argv[2] #the field to get weight values from
    ThresholdValue = sys.argv[3] # the value not to exceed
    
    Path = gp.Describe(InputFC).Path    # Get the full path of the featureclass this includes PGDB name
    PGDBName = os.path.basename(Path) # Get the PGDB full name from Featureclasspath
    
    gp.Workspace = Path                                            #set work space = to featureclass path
    RelTableName = "relationships"
    tbs = gp.ListTables(RelTableName)
    tb = tbs.next()
    if tb: # IF ReltableName exists then
        DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + Path
        conn.Open(DSN)
    
        FeatureclassName = gp.Describe(InputFC).Name
        #gp.AddMessage(Featureclass)
        # look and see if the table valence exists, if it does then delete it
    


        rows = gp.SearchCursor(FeatureclassName) # this search cursor is to loop through all points and get attributes
        row = rows.Next()
        gp.AddMessage("  ")
        gp.AddMessage("Finding All Downstream Features...")
        startList = [] # this holds starting rid values so that if > 1 edge is selected thes new selection set will not exceed a selected value
        ridList = [] # this list holds rid of selected features
        ridWeightList = [] # this list holds ridweight values as the code moves down stream it starts out with the threshold value which is subtracted from with every aditional edge
        count = 0
        while row: # Loop through the features selected by the search query
            ridList.append(row.GetValue("rid"))
            ridWeightList.append(float(ThresholdValue)) # start with threshold value to be subtracted from
            count = count + 1
            row = rows.Next()
        gp.AddMessage("  ")
        gp.AddWarning(str(count) + " Selected features being processed.  If this is too many, hit Cancel.")
        gp.AddMessage(" ")
        startList = startList + ridList
        upstreamWeightList = [] # this will upstream weight values
        upstreamList = [] #this list holds upstream ids as the code moves downstream
        index = 0 # this index is used to get the weight value associated with a rid in the ridList
        for rid in ridList:
            rs = win32com.client.Dispatch(r'ADODB.Recordset')
            querystring = "SELECT relationships.fromfeat, relationships.tofeat, relationships_1.fromfeat AS upstream, " + FeatureclassName + "." + WeightField + " AS down_weight, " + FeatureclassName + "_1." + WeightField + " AS up_weight FROM relationships INNER JOIN " + FeatureclassName + " ON relationships.tofeat = " + FeatureclassName + ".rid, relationships AS relationships_1 INNER JOIN " + FeatureclassName + " AS " + FeatureclassName + "_1 ON relationships_1.fromfeat = " + FeatureclassName + "_1.rid WHERE (((relationships.fromfeat)=" + str(rid) + ") AND ((relationships_1.tofeat)=[relationships].[tofeat]));"
            #querystring = "SELECT relationships.fromfeat, relationships.tofeat, relationships_1.fromfeat AS upstream FROM relationships, relationships AS relationships_1 WHERE (((relationships.fromfeat)=" + str(rid) + ") AND ((relationships_1.tofeat)=[relationships].[tofeat]));"
            #gp.AddMessage(querystring)
            rs.Cursorlocation = 3
            rs.Open(querystring, conn, 1, 3)
            rs.MoveFirst
            orgWeightValue = ridWeightList[index]
            if rs.RecordCount > 0:
                while not rs.EOF:
                    exists = rs.Fields.Item("tofeat").Value in ridList
                    if exists == 0:
                        weightValue = (orgWeightValue - rs.Fields.Item("down_weight").Value)
                        if weightValue >= (0):
                            ridList.append(rs.Fields.Item("tofeat").Value)
                            ridWeightList.append(weightValue)
                            dummy = GetDownstreamFeatures(conn, ridList, ridWeightList, rs.Fields.Item("tofeat").Value, weightValue, FeatureclassName, WeightField)
                            exists = rs.Fields.Item("upstream").Value in ridList
                            #gp.AddMessage("    Evaluating upstream id --> " + str(rs.Fields.Item("upstream").Value) + " with weight " + str(weightValue))
                            if exists == 0:
                                if (orgWeightValue - rs.Fields.Item("up_weight").Value) >= (0):
                                    dummy = GoUpstream(conn, upstreamList, upstreamWeightList, startList, rs.Fields.Item("upstream").Value, (weightValue), FeatureclassName, WeightField)

                    else:
                        exists = rs.Fields.Item("upstream").Value in ridList
                        #gp.AddMessage("    Evaluating upstream id --> " + str(rs.Fields.Item("upstream").Value) + " with weight " + str(weightValue))
                        if exists == 0:
                            if (orgWeightValue - rs.Fields.Item("up_weight").Value) >= (0):
                                #dummy = GoUpstream(conn, upstreamList, upstreamWeightList, startList, rs.Fields.Item("upstream").Value, (weightValue - rs.Fields.Item("up_weight").Value), FeatureclassName, WeightField)
                                dummy = GoUpstream(conn, upstreamList, upstreamWeightList, startList, rs.Fields.Item("upstream").Value, (weightValue), FeatureclassName, WeightField)
                    rs.MoveNext()
            index = index + 1
        #gp.AddMessage("---")
        #gp.AddMessage(str(UpstreamList))
        ridList = ridList + upstreamList
        #gp.AddMessage("  ")
        #gp.AddMessage(str(ridList))

        conn.Close()
        #gp.SelectLayerByAttribute(FeatureclassName, "ADD_TO_SELECTION", "[rid] = 5")
        gp.AddMessage("Populating Selection set with Downstream Features...")
        for rid in ridList:
            string = "rid = " + str(rid)
            gp.SelectLayerByAttribute(FeatureclassName, "ADD_TO_SELECTION", string)
        gp.AddMessage(" ")
        gp.AddWarning("---------------------------------------------------------------------")
        gp.AddWarning("FINISHED --> PLEASE REFRESH YOUR SCREEN TO SHOW SELECTED FEATURES")
        gp.AddWarning("---------------------------------------------------------------------")
        gp.AddMessage(" ")
        gp.AddMessage(" ")
    else:
        gp.AddMessage("  ")
        gp.AddMessage("  ")
        gp.AddError("FEATURE LAYER " + InputFC + " IS NOT A LANDSCAPE NETWORK FEATURE CLASS...")
        gp.AddMessage("  ")
        gp.AddMessage(" ")