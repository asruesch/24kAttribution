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



import arcgisscripting, sys, string, os, re, time, win32com.client, win32api
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()

conn = win32com.client.Dispatch(r'ADODB.Connection')

#Find DownStream Edges
def Finddownstream(fromID, edgelist, edgesFCName, conn):
    querystring = "SELECT relationships.tofeat FROM relationships INNER JOIN " + edgesFCName + " ON relationships.tofeat = " + edgesFCName + ".rid WHERE (((relationships.fromfeat)=" + str(fromID) + "));"
    rs1 = win32com.client.Dispatch(r'ADODB.Recordset')
    rs1.Cursorlocation = 3
    rs1.Open(querystring, conn, 1, 3)
    if rs1.RecordCount > 0:
        rs1.MoveFirst
        fromID = rs1.Fields.Item("tofeat").Value
        exists = fromID in edgelist
        if exists > 0: # This checks to see that the tofeature has not alread been added to list
            return 1
        edgelist.append(fromID)
    else:
        return 1
    
# This calculates the distance between two points between edges given edge and distance lists
def FindNumberOfConfluences(edgeList, ConfluenceList, value, offset):
    ind1 = edgeList.index(value)
    ind1 = ind1 + offset
    NumberConfluence = 0
    count = 0
    for edge in edgeList:
        if count > ind1:
            break
        exists = edge in ConfluenceList
        if exists > 0:
            #gp.AddMessage("     " + str(edge))
            NumberConfluence = NumberConfluence + 1
        count = count + 1
    return NumberConfluence

#Main Function
if __name__ == "__main__":
    try:
        # Input Sampe Points and Edge Netwok Feature classes
        SamplePTS = sys.argv[1] # feature Class (That has been snapped to Geonetwork) to find weighted distance between
        PointIDItem = sys.argv[2] # point FC items used to populate the top and side matrix
        EdgeNetwork = sys.argv[3] # GeoNetwork ...
        OutputTableName = sys.argv[4] # Name of output table the hold weight "Matrix"
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
            matrixIDList.append(row.GetValue(PointIDItem)) # get rids coresponding user-defined id
            SourceEdgeList.append(FID)
            string = string + str(row.GetValue(PointIDItem)) + ","
            row = rows.Next()
        tbs = gp.ListTables(RelTableName)
        tb = tbs.next()
        if tb: # Check to see if Relationships table exists in the workspace. If it does, then run the rest of the code
            print >>ofh, string # print to file
            # get all nodes that have more than one input and populate a list with their tonode ids.  This list will be used to see if a junction is counted or not
            gp.AddMessage("Finding Edge Tonode Confluences...")
            gp.AddMessage(" ")
            querystring = "SELECT noderelationships.tonode FROM noderelationships GROUP BY noderelationships.tonode HAVING (((Count(noderelationships.tonode))>1));"
            rs1 = win32com.client.Dispatch(r'ADODB.Recordset')
            rs1.Cursorlocation = 3
            rs1.Open(querystring, conn, 1, 3)
            NodeList = []
            while not rs1.EOF:
                NodeList.append(rs1.Fields.Item("tonode").Value) # this list hold all edge ids that have Confluence tonodes
                rs1.MoveNext()

            # get edges and their tonode.  Loop through the recordset and add edgeids to list that have a tonode in NOdeList
            querystring = "SELECT noderelationships.rid, noderelationships.tonode FROM noderelationships;"
            rs1 = win32com.client.Dispatch(r'ADODB.Recordset')
            rs1.Cursorlocation = 3
            rs1.Open(querystring, conn, 1, 3)
            ConfluenceList = []
            while not rs1.EOF:
                exists = rs1.Fields.Item("tonode").Value in NodeList
                if exists > 0:
                    ConfluenceList.append(rs1.Fields.Item("rid").Value)
                rs1.MoveNext()
                                          
            NodeList = [] # make NodeList = to nothing
            EdgeSegList = [] # this holds other lists that contain edges from source edge to sink edge used for finding network distance
            count = 0
            for fid in SourceEdgeList:
                edgelist = []
                edgelist.append(fid)
                for edgeID in edgelist:
                    dummy = Finddownstream(edgeID, edgelist, edgesFCName, conn)
                # Add list of edges downstream of a given source edge to a list that hold all edge lists            
                EdgeSegList.append(edgelist) # add list to list
                count = count + 1
       
            gp.AddMessage(" ")
            gp.AddMessage("Creating Distance Matirx --> " + str(OutputTableName))
            gp.AddMessage(" ")
            #gp.AddMessage(str(EdgeSegList))
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
                                #gp.AddMessage("  " + str(edgeList2[0]))
                                valuefound = 0
                                count = 0 # this is the index of the current list element
                                for value1 in edgeList: # This for loop searches for a link in another list
                                    ind2 = value1 in edgeList2
                                    if ind2 > 0: # Value1 (Edgeid) is in the edge list of another point
                                        ind2 = edgeList2.index(value1) # This finds the index value of value1 in the list
                                        if ind2 > 0: # if the index value is not at the first element
                                            if count == 0: # if link confluence is the first element of list
                                                #POINT IS DOWNSTREAM 
                                                #gp.AddMessage("   Upstream")
                                                confluenceCount = FindNumberOfConfluences(edgeList2, ConfluenceList, value1, -1)
                                            else:
                                                #POINT IS ON A BRANCH
                                                #gp.AddMessage("   Branch")
                                                confluenceCount = FindNumberOfConfluences(edgeList, ConfluenceList, value1, 1)
                                                confluenceCount = confluenceCount + FindNumberOfConfluences(edgeList2, ConfluenceList, value1, -1) - 1
                                        else: # this is if the point is at the 0 element of list edgelist2 meaning that is is directly downstream
                                            #POINT IS DOWNSTREAM
                                            #gp.AddMessage("   Downstream")
                                            confluenceCount = FindNumberOfConfluences(edgeList, ConfluenceList, value1, -1)
                                        valuefound = 1
                                        string = string + str(confluenceCount) + ","
                                        break
                                    count = count + 1
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
            gp.AddMessage(" ")
            gp.AddWarning("FINISHED Number of Confluences (Symmetric) Script")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
        else: # Relationship table doesn't exist in geodatabase
            gp.AddMessage("Operation Terminated -> Relationship table doesn't exists in GeoDatabase")
        ofh.close() # close file
    except:
        gp.GetMessages()