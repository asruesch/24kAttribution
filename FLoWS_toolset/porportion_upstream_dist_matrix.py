# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Build Bi-Directional weights         ~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Between Features in a Feature Class  ~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# This script finds bi-directional weighted values between all
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


import win32com.client, sys, string, os, win32api, re, time

gp = win32com.client.Dispatch("esriGeoprocessing.GPDispatch.1")
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
        DistanceItem = sys.argv[4]
        OutputTableName = sys.argv[5] # Name of output table the hold weight "Matrix"
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
        gp.AddMessage("Building Edge Node relationship List")
        string = " ,"
        while row: # Loop through the features selected by the search query
            FID = row.rid
            edgeRows = gp.SearchCursor(edgesFCName, "[rid] = " + str(FID)) # This cursor is opened to get edge length to calc edge length
            edgeRow = edgeRows.Next()
            edgeDistance = edgeRow.GetValue(DistanceItem)  # Get the total edge length
            matrixIDList.append(row.GetValue(PointIDItem)) # get rids coresponding user-defined id
            distratio = row.ratio # get line ratio from point featureclass
            SourceEdgeDistList.append(edgeDistance * distratio)
            SourceEdgeList.append(FID)
            string = string + str(row.GetValue(PointIDItem)) + ","
            row = rows.Next()
        tbs = gp.ListTables(RelTableName)
        tb = tbs.next()
        if tb: # Check to see if Relationships table exists in the workspace. If it does, then run the rest of the code
            print >>ofh, string # print to file 
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
            
           
            gp.AddMessage("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            gp.AddMessage("~~~~~~~~~~~~~~~~~~~~ Evaluating Lists ~~~~~~~~~~~~~~~")
            gp.AddMessage("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            # This loop goes through each element in each edge looking for common edegs to lint the two list and calc distance
            Index1 = 0 # This index keeps track of what Edgelist is being accessed
            #gp.AddMessage(str(EdgeSegList))
            for edgeList in EdgeSegList:
                string = ""
                string = str(matrixIDList[Index1]) + ","
                #gp.AddMessage(str(edgeList[0]))
                count1 = len(edgeList) # number of elements in List
                sink1 = edgeList[count1 - 1] # this is the sink feature used to check to see if search list has sink
                #gp.AddMessage("sink --> " + str(sink1))
                Index2 = 0 # this keeps track of what edgelist is being searched
                for edgeList2 in EdgeSegList: # list to search for value in first list
                        if Index1 <> Index2: # make sure that the same list is being searched
                            #gp.AddMessage(str(edgeList2))
                            exists = sink1 in edgeList2 # look for sink value to make sure the search list is in the same network
                            if exists > 0:
                                #gp.AddMessage("in drainage")
                                valuefound = 0
                                #count = 0 # this is the index of the current list element
                                for value1 in edgeList: # This for loop searches for a link in another list
                                    ind2 = value1 in edgeList2
                                    if ind2 > 0: # if value1 is in edgeList2 then you know that can find their link in FindDistance Function
                                        ind2 = edgeList2.index(value1) # This finids the index value of value1 in list
                                        if ind2 > 0: # if the index value is not at first element
                                            distanceDown = FindDistance(edgeList, EdgeSegDistList[Index1], value1, 0)
                                            totalDistance = distanceDown + FindDistance(edgeList2, EdgeSegDistList[Index2], value1, 0)
                                            distance = distanceDown / totalDistance
                                            gp.AddMessage(str(distance))
                                            if distance < 1:
                                                distance = float(1 - distance) # this get the upstream proportion
                                        else:
                                            distance = 1
                                        valuefound = 1
                                        string = string + str(distance) + ","
                                        break
                                    #count = count + 1
                                if valuefound == 0: 
                                    string = string + "-1,"
                                    #gp.AddMessage("point not in list")
                            else:# this is the case if the points are not in the same drainage
                                string = string + "-1,"
                                #gp.AddMessage("Point not in drainage")
                        else:
                            string = string + "0,"
                            #gp.AddMessage("same Point")
                        Index2 = Index2 + 1 # this number keeps track of search list number
                print >>ofh, string 
                Index1 = Index1 + 1 # This keeps track of search value list
        else: # Relationship table doesn't exist in geodatabase
            gp.AddMessage("Operation Terminated -> Relationship table doesn't exists in GeoDatabase")
        gp.AddMessage("Finished")
        ofh.close() # close file
    except:
        gp.GetMessages()