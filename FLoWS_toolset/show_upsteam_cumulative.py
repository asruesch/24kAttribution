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
def GetupstreamFeatures(conn, ridList, weightList, id, weightValue, FeatureclassName, WeightField):
    rs = win32com.client.Dispatch(r'ADODB.Recordset')
    querystring = "SELECT relationships.fromfeat, relationships.tofeat, " + FeatureclassName + "." + WeightField + " AS weight FROM relationships INNER JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid WHERE (((relationships.tofeat)=" + str(rid) + "));"
    rs.Cursorlocation = 3
    rs.Open(querystring, conn, 1, 3)
    rs.MoveFirst
    if rs.RecordCount > 0:
        while not rs.EOF:
            exists = rs.Fields.Item("fromfeat").Value in ridList
            if exists == 0:
                if (weightValue - rs.Fields.Item("weight").Value) >= 0:
                    weightList.append(weightValue - rs.Fields.Item("weight").Value)
                    ridList.append(rs.Fields.Item("fromfeat").Value)
            rs.MoveNext()
    rs = "Nothing"
    return 1
if __name__ == "__main__":

    InputFC = sys.argv[1]       # Input Feature Class
    WeightField = sys.argv[2]   # Weight field
    ThresholdValue = sys.argv[3] # Weight Field value that subtracted from until 0
    
    Path = gp.Describe(InputFC).Path    # Get the full path of the featureclass this includes PGDB name
    gp.Workspace = Path                                            #set work space = to featureclass path
    RelTableName = "relationships"
    tbs = gp.ListTables(RelTableName)
    tb = tbs.next()
    if tb: # IF ReltableName exists then
        PGDBName = os.path.basename(Path)                               # Get the PGDB full name from Featureclasspath
    
        DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + Path
        conn.Open(DSN)
    
        FeatureclassName = gp.Describe(InputFC).Name
        #gp.AddMessage(Featureclass)
        # look and see if the table valence exists, if it does then delete it

        ridList = [] # this list holds rid of selected features
        weightList = [] # this list holds weight values for a rid
        rows = gp.SearchCursor(FeatureclassName) # this search cursor is to loop through all points and get attributes
        row = rows.Next()
        gp.AddMessage(" ")
        gp.AddMessage("Getting Selected Features....")
        gp.AddMessage(" ")
        count = 0
        while row: # Loop through the features selected by the search query
            ridList.append(row.GetValue("rid"))
            weightList.append(float(ThresholdValue))
            count = count + 1
            row = rows.Next()
        gp.AddMessage(" ")
        gp.AddWarning(str(count) + " Selected features being processed.  If this is too many, hit Cancel.")
        gp.AddMessage(" ")
        index = 0
        gp.AddMessage("Finding All Upstream Features That Area within " + str(ThresholdValue) + " of Selected Features....")
        gp.AddMessage(" ")
        for rid in ridList:
            rs = win32com.client.Dispatch(r'ADODB.Recordset')
            querystring = "SELECT relationships.fromfeat, relationships.tofeat, " + FeatureclassName + "." + WeightField + " AS weight FROM relationships INNER JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid WHERE (((relationships.tofeat)=" + str(rid) + "));"
            #gp.AddMessage(querystring)
            rs.Cursorlocation = 3
            rs.Open(querystring, conn, 1, 3)
            rs.MoveFirst
            if rs.RecordCount > 0:
                while not rs.EOF:
                    exists = rs.Fields.Item("fromfeat").Value in ridList
                    if exists == 0:
                        weightValue = weightList[index] - rs.Fields.Item("weight").Value
                        if weightValue >= 0:
                            ridList.append(rs.Fields.Item("fromfeat").Value)
                            weightList.append(weightValue)
                            #value = GetupstreamFeatures(conn, ridList, weightList, rs.Fields.Item("fromfeat").Value, weightValue, FeatureclassName, WeightField)
                            value = GetupstreamFeatures(conn, ridList, weightList, rs.Fields.Item("fromfeat").Value, weightList[index], FeatureclassName, WeightField)
                    rs.MoveNext()
            index = index + 1
        #gp.AddMessage(str(ridList))
        conn.Close()
        #gp.SelectLayerByAttribute(FeatureclassName, "ADD_TO_SELECTION", "[rid] = 5")
        gp.AddMessage("Adding Features To Selection Set....")
        for rid in ridList:
            string = "rid = " + str(rid)
            gp.SelectLayerByAttribute(FeatureclassName, "ADD_TO_SELECTION", string)
        gp.AddMessage(" ")
        gp.AddWarning("---------------------------------------------------------------------")
        gp.AddWarning("FINISHED --> PLEASE REFRESH YOUR SCREEN TO SHOW SELECTED FEATURES ...")
        gp.AddWarning("---------------------------------------------------------------------")
        gp.AddMessage(" ")
        gp.AddMessage(" ")
    else:
        gp.AddMessage("  ")
        gp.AddMessage("  ")
        gp.AddError("FEATURE LAYER " + InputFC + " IS NOT A LANDSCAPE NETWORK FEATURE CLASS...")
        gp.AddMessage("  ")
        gp.AddMessage(" ")