# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Calculate Stream Order (Strahler)  ~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# This scrip calculates and populates a output field with an edges
# stream order as defined by Strahler

# ~~~~~~~~~~~~~~~~  Contact Information ~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~ Dave Theobald (Natural Resources Ecology Lab - NREL)  ~~~~~
# ~~~     Colorado State University, Fort Collins CO         ~~~~~
# ~~~     e-mail: davet@nrel.colostate.edu                   ~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create by: John Norman 9/7/04
# Last Modified: 9/9/04

# Create the geoprocessor

import arcgisscripting, sys, string, os, re, time, win32com.client, win32api
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()

conn = win32com.client.Dispatch(r'ADODB.Connection')


try:

    InputFC = sys.argv[1]  #Input edge Feature Class
    NodeFC = sys.argv[2] #Input node feature class
    NodeCatField = sys.argv[3] #Field that holds Node catagories (source, outlet....)
    OutField = sys.argv[4] #Field to add oredr value to

    Path = gp.Describe(InputFC).Path    # Get the full path of the featureclass this includes PGDB name
    FeatureclassPath = Path
    PGDBName = os.path.basename(Path)                               # Get the PGDB full name from Featureclasspath
    FullFeatureclassPath = Path
    #gp.AddMessage(Path)

    
    gp.Workspace = Path                                            #set work space = to featureclass path
    DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + Path
    conn.Open(DSN)
    
    FeatureclassName = gp.Describe(InputFC).Name
    NodeFeatureclassName = gp.Describe(NodeFC).Name
    
    RelTableName = "relationships"
    # AccField = "shape_length"
    
    # look and see if the table valence exists, if it does then delete it    
    tbs = gp.ListTables(RelTableName)
    tb = tbs.next()

    if tb: # IF ReltableName exists then.... 
        rs = win32com.client.Dispatch(r'ADODB.Recordset')
        # rs_name = RelTableName
        querystring = "SELECT " + FeatureclassName + ".rid FROM " + FeatureclassName + " LEFT JOIN relationships ON " + FeatureclassName + ".rid = relationships.tofeat WHERE (((" + FeatureclassName + ".rid) Is Not Null) AND ((relationships.tofeat) Is Null));"
        rs.Open(querystring, conn, 1)
        #gp.AddMessage(querystring)
        rs.MoveFirst
        count = 0
        # Populate featurelist with first order streams
        FeatureList = [] # this list holds feature IDs that have been added or accumulated
        StreamOrderValueList = [] # this list holds added or accumulated feature values
        CountList = [] # this list holds the number of times a edge has been used to calculate stream order
        gp.AddMessage(" ")
        gp.AddMessage("Finding First Order Streams.....")
        gp.AddMessage(" " )
        while not rs.EOF:
            FeatureList.append(rs.Fields.Item("rid").Value) # add rid of first order stream to featurelist
            StreamOrderValueList.append(1) # add a value of one since it is a first order stream
            CountList.append(1) # this couns the number of times it has been accessed
            rs.MoveNext()
        gp.AddMessage("Calculating nth Order Streams....")
        gp.AddMessage(" ")
        FeatureList2 = []
        StreamOrderValueList2 = []
        index = 0
        #this loop startes at first order streams and moves down stream
        for FID in FeatureList:
            FeatureList3 = []
            StreamOrderValueList3 = []
            
            #gp.AddMessage("FID: " + str(FID))
            fromorder = StreamOrderValueList[index]
            
            FeatureList2.append(FID)
            StreamOrderValueList2.append(fromorder)
            
            FeatureList3.append(FID)
            StreamOrderValueList3.append(fromorder)
            index2 = 0
            for FID3 in FeatureList3:
                #gp.AddMessage("    FID3 :" + str(FID3))
                fromorder2 = StreamOrderValueList3[index2]
                #this query gets a downstream feature from feature FID3
                querystring = "SELECT " + FeatureclassName + ".rid, relationships.tofeat FROM " + FeatureclassName + " INNER JOIN relationships ON " + FeatureclassName + ".rid = relationships.fromfeat WHERE (((" + FeatureclassName + ".rid)=" + str(FID3) + "));"
                #gp.AddMessage("    query1: " + querystring)
                rs = win32com.client.Dispatch(r'ADODB.Recordset')
                rs.Open(querystring, conn, 1)
                rs.MoveFirst
                stop = 0
                while not rs.EOF:               
                    tofeature = rs.Fields.Item("tofeat").Value
                    #gp.AddMessage("       " + str(tofeature))
                    # this querys looks back upstream from tofeat to find what edges drain into it
                    #querystring = "SELECT relationships.fromfeat FROM relationships WHERE (((relationships.fromfeat)<>" + str(FID3) + ") AND ((relationships.tofeat)=" + str(tofeature) + "));"
                    # this query looks back upstream from tofeature to find what edges drian into it and what the fromnode catagory is
                    querystring = "SELECT relationships.fromfeat, " + NodeFeatureclassName + "." + NodeCatField + " FROM relationships INNER JOIN (noderelationships INNER JOIN nodes ON noderelationships.fromnode = " + NodeFeatureclassName + ".pointid) ON relationships.fromfeat = noderelationships.rid WHERE (((relationships.fromfeat)<>" + str(FID3) + ") AND ((relationships.tofeat)=" + str(tofeature) + "));"
                    #gp.AddMessage("           query2: " + querystring)
                    rs1 = win32com.client.Dispatch(r'ADODB.Recordset')
                    rs1.Open(querystring, conn, 1)
                    rs1.MoveFirst
                    if not rs1.EOF: #if there are records than there is a junction 
                        juncexists = rs1.Fields.Item("fromfeat").Value in FeatureList2
                        nojunction = 0
                    else:
                        juncexists = 0
                        nojunction = 1
                    exists = tofeature in FeatureList3
                    if exists == 1: # if feature in list then it is in a loop break loop and set stop equal to one so for loop is broken
                        stop = 1
                        #break
                    exists = tofeature in FeatureList2
                    if exists == 1: # if the tofeature exists in featurelist2 then evaluate its position
                        ind = FeatureList2.index(tofeature) # this is the index of the feature in featurelist2 to get the order value from streamordervaluelist2
                        toorder = StreamOrderValueList2[ind] # this is the stream order of the tofeature
                        if juncexists == 1: # this is if the junction coming into the tofeature has been calculated if it has what is its value
                            ind2 = FeatureList2.index(rs1.Fields.Item("fromfeat").Value) # the index of the feature in featurelist2
                            if fromorder2 == StreamOrderValueList2[ind2]:
                                if rs1.Fields.Item(NodeCatField).Value <> "Downstream Divergence":
                                    #gp.AddMessage("               Downstream Divergence dosen't Exists")
                                    StreamOrderValueList2[ind] = fromorder2 + 1
                                    fromorder2 = fromorder2 + 1
                                else:
                                    #gp.AddWarning("               Downstream Divergence Exists")
                                    StreamOrderValueList2[ind] = fromorder2
                                    fromorder2 = fromorder2
                            elif fromorder2 > StreamOrderValueList2[ind2]:
                                StreamOrderValueList2[ind] = fromorder2
                            else:
                                stop = 1
                        else:
                            StreamOrderValueList2[ind] = fromorder2
                            
                        if nojunction == 1:
                            StreamOrderValueList2[ind] = fromorder2
                         
                    else:
                        FeatureList2.append(tofeature)
                        StreamOrderValueList2.append(fromorder2)
                    FeatureList3.append(tofeature)
                    StreamOrderValueList3.append(fromorder2)
                    rs.MoveNext()
                index2 = index2 + 1
                if stop == 1:
                    stop = 0
                    break
            index = index + 1

        conn.Close()
        #ind = 0
        #gp.AddMessage("---")
        #for value in FeatureList:
            #gp.AddMessage(str(value) + "," + str(StreamOrderValueList[ind]) + "," + str(CountList[ind]))
            #ind = ind + 1
        #gp.AddMessage("----------------")
        if gp.ListFields(FeatureclassName, OutField).Next():
            gp.AddMessage("Populating Field " + OutField + "....")
        else:
            gp.AddMessage("Populating Field " + OutField + "....")
            gp.AddField(FeatureclassName, OutField, "double")
        gp.AddMessage(" ")
        #calcfield =  "[" + AccField + "]"
        #gp.CalculateField(FeatureclassName, OutField, "1")

        count = 0
        for FID in FeatureList2:
            if FID <> -1:
                querystring = "rid = " + str(FID)
                #gp.AddMessage(str(FID))
                Rows = gp.UpdateCursor(FeatureclassName, querystring)
                Row = Rows.Next()
                while Row:
                    Row.SetValue(OutField, StreamOrderValueList2[count])
                    Rows.UpdateRow(Row)
                    Row = Rows.Next()
            count = count + 1
        gp.AddMessage(" ")
        gp.AddMessage(" ")
        gp.AddWarning("Finshed Calculate Stream Order (Strahler) Script")
        gp.AddMessage(" ")
        gp.AddMessage(" ")
        gp.AddMessage(" ")
    else:
        gp.AddMessage("Relationship table doesn't exist")
        

except:
    print gp.GetMessages(0)
    print conn.GetMessages()
    
    