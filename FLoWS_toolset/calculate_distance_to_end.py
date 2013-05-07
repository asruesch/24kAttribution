# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Populates a user-defined field that  ~~~~~~~~
# ~~~~~~~~~~~~~~~~~  contains distance from feature to the  ~~~~~~
# ~~~~~~~~~~~~~~~~~ end of a drainage     ~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~~~~~  Contact Information ~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~ Dave Theobald ( Natural Resources Ecology Lab - NREL)  ~~~~~
# ~~~     Colorado State University, Fort Collins CO         ~~~~~
# ~~~     e-mail: davet@nrel.colostate.edu                   ~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create by: John Norman 9/14/04
# Last Modified: 9/21/04



import arcgisscripting, sys, string, os, re, time, win32com.client, win32api
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()

conn = win32com.client.Dispatch(r'ADODB.Connection')

#Find DownStream Edges
def Finddownstream(fromID, edgelist, edgeDistList, edgesFCName, DistanceItem, conn):
    querystring = "SELECT relationships.tofeat, " + edgesFCName + "." + DistanceItem + " FROM relationships INNER JOIN " + edgesFCName + " ON relationships.tofeat = " + edgesFCName + ".rid WHERE (((relationships.fromfeat)=" + str(fromID) + "));"
    rs1 = win32com.client.Dispatch(r'ADODB.Recordset')
    rs1.Cursorlocation = 3
    rs1.Open(querystring, conn, 1, 3)
    if rs1.RecordCount > 0:
        rs1.MoveFirst
        fromID = rs1.Fields.Item("tofeat").Value
        dist = rs1.Fields.Item(DistanceItem).Value
        exists = fromID in edgelist
        if exists > 0: # This checks to see that the tofeature has not alread been added to list
            return 1
        edgelist.append(fromID)
        edgeDistList.append(dist)
        #dummy = Finddownstream(fromID, edgelist, edgeDistList, edgesFCName, DistanceItem, conn)
    else:
        return 1
    
# This calculates the distance between two points between edges given edge and distance lists
def FindDistance(distList):
    distance = 0
    for value in distList:
        distance = distance + value
    return distance

#Main Function
if __name__ == "__main__":
    try:
        # Input Sampe Points and Edge Netwok Feature classes
        SamplePTS = sys.argv[1] # feature Class (That has been snapped to Geonetwork) to find weighted distance between
        UniqueIDField = sys.argv[2] # this is a field that holds a unique ID for every feature it is nessary to relate distances back to the same feature
        EdgeNetwork = sys.argv[3] # GeoNetwork ...
        DistanceItem = sys.argv[4] # edge of rca field
        OutField = sys.argv[5] # this is the name of the field that will be populated wil distance information
        RelTableName = "relationships" # table in GeoNetwork PGDB that hold feature relationships


        PGDBPath = gp.Describe(EdgeNetwork).Path # get the path of the Landscape network
        sampleFCName = gp.Describe(SamplePTS).Name
        edgesFCName = gp.Describe(EdgeNetwork).Name

        DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + PGDBPath
        conn.Open(DSN)
        
        gp.workspace = PGDBPath
        SourceEdgeList = [] # this list holds source edges to calc distance matrix
        UniqueIDList = [] # this list holds unique ids for a feature so it can be updated with the right value
        SourceEdgeDistList = [] # This list holds distance from point location to end of edge
        rows = gp.SearchCursor(SamplePTS) # this search cursor is to loop through all points and get attributes
        row = rows.Next()
        gp.AddMessage(" ")
        gp.AddMessage("Calculating Distances....")
        gp.AddMessage(" ")
        while row: # Loop through the features selected by the search query
            FID = row.rid
            edgeRows = gp.SearchCursor(edgesFCName, "[rid] = " + str(FID)) # This cursor is opened to get edge length to calc edge length
            edgeRow = edgeRows.Next()
            edgeDistance = edgeRow.GetValue(DistanceItem)  # Get the total edge length
            UniqueIDList.append(row.GetValue(UniqueIDField)) # Get the unique ID for a feature
            distratio = row.ratio # get line ratio from point featureclass
            SourceEdgeDistList.append(edgeDistance * distratio)
            SourceEdgeList.append(FID)
            row = rows.Next()
        tbs = gp.ListTables(RelTableName)
        tb = tbs.next()
        if tb: # Check to see if Relationships table exists in the workspace. If it does, then run the rest of the code
            
            gp.AddMessage(" ")
            gp.AddMessage("Evaluating Point Distances....")
            gp.AddMessage(" ")
            
            EdgeSegList = [] # this holds other lists that contain edges from source edge to sink edge used for finding network distance
            EdgeSegDistList = [] # This holds a list of lists containg edge lenghts
            count = 0
            for fid in SourceEdgeList:
                edgelist = []
                edgeDistList = []
                edgelist.append(fid)
                edgeDistList.append(SourceEdgeDistList[count])
                for edgeID in edgelist:
                    dummy = Finddownstream(edgeID, edgelist, edgeDistList, edgesFCName, DistanceItem, conn)
                # Add list of edges downstream of a given source edge to a list that hold all edge lists            
                EdgeSegList.append(edgelist) # add list to list
                EdgeSegDistList.append(edgeDistList)
                count = count + 1
            conn.Close()

            if gp.ListFields(sampleFCName, OutField).Next():
                gp.AddMessage("Populating Field " + OutField + "....")
            else:
                gp.AddMessage("Populating Field " + OutField + "....")
                gp.AddField(sampleFCName, OutField, "double")
            gp.AddMessage(" ")
            # calcfield =  "[" + AccField + "]"
            #gp.CalculateField(sampleFCName, OutField, "0")

            count = 0
            for ID in UniqueIDList:
                querystring = UniqueIDField + " = " + str(ID)
                Rows = gp.UpdateCursor(sampleFCName, querystring) # find feature to update dist record
                Row = Rows.Next()
                distance = FindDistance(EdgeSegDistList[count])
                while Row:
                    Row.SetValue(OutField, distance)
                    Rows.UpdateRow(Row)
                    Row = Rows.Next()
                count = count + 1
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            gp.AddWarning("Finished Calculate Points Downstream Distance to Basin Outlet Script")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            
        else: # Relatiionship table doesn't exist in geodatabase
            gp.AddMessage("Operation Terminated -> Relationship table doesn't exists in GeoDatabase")
    except:
        gp.GetMessages()