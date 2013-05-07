# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Build Directional weights            ~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Between Features in a Feature Class  ~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# This script finds directional weighted values between all
# features within the input feature class.  The weighted value
# (distance) is calculated using the input GeoNetwork summing
# on an edge attribute values between features.  

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
def FindDistance(edgeList, distList1, value, offset):
    ind1 = value in edgeList
    ind1 = edgeList.index(value)
    distance = 0
    for x in range(ind1 + offset):
        distance = distance + distList1[x]
    return distance

#Main Function
if __name__ == "__main__":
    try:
        # Input Sampe Points and Edge Netwok Feature classes
        SamplePTS = sys.argv[1] # feature Class (That has been snapped to Geonetwork) to find weighted distance between
        PointIDItem = sys.argv[2] # point FC items used to populate the top and side matrix
        EdgeNetwork = sys.argv[3] # GeoNetwork ...
        LocalDistanceItem = sys.argv[4] # this is the local value for a feature section it can be the local value that the accumulated value was calculated off of
        DistanceItem = sys.argv[5] # This is the accumulated field or a field that contains ratio values
        OutputTableName = sys.argv[6] # Name of output table the hold weight "Matrix"
        RelTableName = "relationships" # table in GeoNetwork PGDB that hold feature relationships
        #DistanceItem = "Shape_Length" # Attribute value in GeoNetwork that weight matrix will built off of
        
        PGDBPath = gp.Describe(EdgeNetwork).Path # get the path of the Landscape network
        sampleFCName = gp.Describe(SamplePTS).Name
        edgesFCName = gp.Describe(EdgeNetwork).Name

        List = os.path.split(OutputTableName)
        FullDistTableName = List[1]

        ofh = open(OutputTableName, "w")
        DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + PGDBPath
        conn.Open(DSN)
        gp.workspace = PGDBPath
        SourceEdgeList = [] # this list holds source edges to calc distance matrix
        matrixIDList = [] # this list holds sample point ids (user-defined).  It is used to create the header and side protion of the matrix.
        SourceEdgeDistList = [] # This list holds distance from point location to end of edge
        rows = gp.SearchCursor(SamplePTS) # this search cursor is to loop through all points and get attributes
        row = rows.Next()
        gp.AddMessage(" ")
        gp.AddMessage("Getting Point Features....")
        gp.AddMessage(" ")
        string = " ,"
        while row: # Loop through the features selected by the search query
            FID = row.rid
            edgeRows = gp.SearchCursor(edgesFCName, "[rid] = " + str(FID)) # This cursor is opened to get edge length to calc edge length
            edgeRow = edgeRows.Next()
            edgeDistance = edgeRow.GetValue(DistanceItem)  # Get the total edge length
            edgeLocalDistance = edgeRow.GetValue(LocalDistanceItem) # this is the local distance value that is used to get the local distance using the ratio value associated with the point
            matrixIDList.append(row.GetValue(PointIDItem)) # get rids coresponding user-defined id
            distratio = row.ratio # get line ratio from point featureclass
            SourceEdgeDistList.append(edgeDistance + (edgeLocalDistance * (1 - distratio)))
            SourceEdgeList.append(FID)
            string = string + str(row.GetValue(PointIDItem)) + ","
            row = rows.Next()
        tbs = gp.ListTables(RelTableName)
        tb = tbs.next()
        if tb: # Check to see if Relationships table exists in the workspace. If it does, then run the rest of the code
            print >>ofh, string
            EdgeSegList = [] # this holds other lists that contain edges from source edge to sink edge used for finding network distance
            #EdgeSegDistList = [] # This holds a list of lists containg edge lenghts
            count = 0
            gp.AddMessage("Getting Point Distances....")
            for fid in SourceEdgeList:
                edgelist = []
                edgeDistList = []
                edgelist.append(fid)
                #edgeDistList.append(SourceEdgeDistList[count])
                for edgeID in edgelist:
                    dummy = Finddownstream(edgeID, edgelist, edgeDistList, edgesFCName, DistanceItem, conn)
                # Add list of edges downstream of a given source edge to a list that hold all edge lists            
                EdgeSegList.append(edgelist) # add list to list
                #EdgeSegDistList.append(edgeDistList)
                count = count + 1
            
           
            gp.AddMessage(" ")
            gp.AddMessage("Creating Distance Matirx --> " + str(OutputTableName))
            gp.AddMessage(" ")
            # This loop goes through each element in each edge looking for common edegs to link the two list and calc ratio
            Index1 = 0 # This index keeps track of what Edgelist is being accessed
            for edgeList in EdgeSegList:
                #gp.AddMessage(str(edgeList))
                startEdge = edgeList[0]
                string = ""
                string = str(matrixIDList[Index1]) + ","
                index = 0
                for SourceEdge in SourceEdgeList:
                    if SourceEdge <> startEdge: # this is for the same edge or point ID
                        exists = SourceEdge in edgeList
                        if exists > 0:
                            #gp.AddMessage("    " + str(SourceEdge))
                            #gp.AddMessage(str(SourceEdgeDistList[Index1] ) + "/" + str(SourceEdgeDistList[index]))
                            ratio = SourceEdgeDistList[Index1] / SourceEdgeDistList[index]
                            string = string + str(ratio) + ","
                        else:
                            string = string + "-1,"
                    else: # point are on the dame edge... need to check if it is the same point or diffrent points. If they are diffrent points check position
                        if SourceEdgeDistList[Index1] == SourceEdgeDistList[index]: # if ratio lengths are equal same point
                            string = string + "0,"
                        elif SourceEdgeDistList[Index1] < SourceEdgeDistList[index]: # if Index1 is less then index distance Index1 is below it index 
                            string = string + "1,"
                        else:
                            #ratio = SourceEdgeDistList[Index1] / SourceEdgeDistList[index]
                            #string = string + str(ratio) + ","
                            string = string + "-1,"
                            
                    index = index + 1
                print >>ofh, string
                Index1 = Index1 + 1
            gp.AddMessage(" ")
            gp.AddWarning("FINISHED Ratio of Upstream to Downstream (Asymmetric) Script")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
        else: # Relationship table doesn't exist in geodatabase
            gp.AddMessage("Operation Terminated -> Relationship table doesn't exists in GeoDatabase")
        ofh.close() # close file
    except:
        gp.GetMessages()