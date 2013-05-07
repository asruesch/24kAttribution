
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~  Resolves Braided Stream Channels  ~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


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


#def GetDownstreamFeatures(conn, ridList, id):
def GetDownstreamFeatures(conn, list1, list2, list3, fid, ChannelTableName, WeightField, weight, UserCrit, orgIndex):
    #gp.AddMessage("in function")
    rs2 = win32com.client.Dispatch(r'ADODB.Recordset')
    querystring = "SELECT " + ChannelTableName + ".tofeat, " + FeatureclassName + "." + WeightField + " AS weight FROM " + ChannelTableName + " INNER JOIN " + FeatureclassName + " ON " + ChannelTableName + ".tofeat = " + FeatureclassName + ".rid WHERE (((" + ChannelTableName+ ".fromfeat)=" + str(fid) + "));"
    #gp.AddMessage(querystring)
    rs2.Cursorlocation = 3
    rs2.Open(querystring, conn, 1, 3)
    rs2.MoveFirst
    if rs2.RecordCount > 0: # if there are no records then it is an outlet node
        while not rs2.EOF:
            exists = rs2.Fields.Item("tofeat").Value in list1
            if exists == 0:
                list1.append(rs2.Fields.Item("tofeat").Value)
                list2.append(rs2.Fields.Item("weight").Value + weight)
                list3.append(0)
            else: # this is to find min or max path based on user-defined pram....
                index = list1.index(rs2.Fields.Item("tofeat").Value)
                if UserCrit == "Maximum":
                    if list2[index] < (rs2.Fields.Item("weight").Value + weight):
                        list2[index] = (rs2.Fields.Item("weight").Value + weight)
                else:
                    if list2[index] > (rs2.Fields.Item("weight").Value + weight):
                        list2[index] = (rs2.Fields.Item("weight").Value + weight)                
            rs2.MoveNext()
    else:
        #gp.AddMessage("index " + str(orgIndex))
        list3[orgIndex] = 1 # outlet found -- this is so all outlet can be IDed easly and evaluated between divergent edge
        
    rs2 = "Nothing"
    return 1
def FindLocalChannel(DownstreamList, weightList, outletList, conn, ChannelTableName, UserCrit, listCount, OrgFrom):
    outletCountList = [] # this list holds the count of common outlet edges relative to the first element in DownstreamList
    orgoutletCountList = [] # this retains the org count to see if any outlet edges are the same
    sumWeightList = [] # this list holds the sum of downstream edges 
    count = 0
    while count <= (listCount - 1): # this loop counts up the number of outlet edges to be subtracted from to find divergent streams that converge at the same outlet edges
        outletcount = 0
        sumweight = 0
        count1 = 0
        for outlet in outletList[count]:
            if outlet == 1:
                outletcount = outletcount + 1
                sumweight = sumweight + weightList[count][count1]
            count1 = count1 + 1
        outletCountList.append(outletcount)
        orgoutletCountList.append(outletcount)
        sumWeightList.append(sumweight)
        count = count + 1
    outcount = 0
    #gp.AddWarning("  " + str(outletCountList))
    for outlet in outletList[0]: # loop throught the first element in DownstreamList outletnodes to find common nodes in other lists
        if outlet == 1:
            outletCountList[0] = outletCountList[0] - 1
            count = 1
            while count <= (listCount - 1): # this loop evaluates outlet node for the rest of the divergent edges to see if they have the same outlet edges
                exists2 = DownstreamList[0][outcount] in DownstreamList[count]
                if exists2 == 1:
                    outletCountList[count] = outletCountList[count] - 1
                count = count + 1
        outcount = outcount + 1
    #gp.AddWarning("  " + str(outletCountList))

    sameOutlet = 0 # all divergent edges have the same outlet egdes
    for value in outletCountList: # a value > 0 is the not all edges have the same outelt
        if value > 0:
            sameOutlet = 1
            
    removeEdgeList = []
    rs2 = win32com.client.Dispatch(r'ADODB.Recordset')
    count = 0
    #while count <= (listCount - 1):
    for value in outletCountList:
        count1 = count + 1
        while count1 <= (listCount - 1):
            #if outletCountList[count] <> outletCountList[count1]: # if they don't have the same outlet edges ...
            if sameOutlet == 1:
                if outletCountList[count1] <> orgoutletCountList[count1]: # if there are no outlet edges that match
                    #gp.AddMessage("    Need to evaluate")
                    count2 = 0
                    while count2 <= (listCount - 1):
                        index1 = 0
                        if count2 < (listCount - 1):
                            for rid in DownstreamList[count2]:
                                if index1 <> 0:
                                    count3 = count2 + 1
                                    while count3 <= (listCount - 1):
                                        edgeExists = rid in DownstreamList[count3]
                                        if edgeExists > 0:
                                            index2 = DownstreamList[count3].index(rid)
                                            rs1 = win32com.client.Dispatch(r'ADODB.Recordset')
                                            querystring = "SELECT " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".tofeat)=" + str(DownstreamList[count3][index2]) + "));"
                                            rs1.Open(querystring, conn, 1)
                                            fromList  = []
                                            toList = []
                                            rs1.MoveFirst
                                            while not rs1.EOF:
                                                fromList.append(rs1.Fields.Item("fromfeat").Value)
                                                toList.append(rs1.Fields.Item("tofeat").Value)
                                                rs1.MoveNext()
                                            rs1 = "nothing"
                                            if UserCrit == "Maximum":
                                                if weightList[count2][index1] < weightList[count3][index2]:
                                                    upcount = 0
                                                    for fromfeat in fromList:
                                                        fromexists1 = fromfeat in DownstreamList[count3]
                                                        fromexists2 = fromfeat in DownstreamList[count2]
                                                        if fromexists1 < 1 and fromexists2 > 0 :
                                                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(fromfeat) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(toList[upcount]) + "));"
                                                            rs2.Open(querystring, conn, 1, 3)
                                                            removeEdgeList.append(fromfeat)
                                                        upcount = upcount + 1
                                                else:
                                                    upcount = 0
                                                    for fromfeat in fromList:
                                                        fromexists1 = fromfeat in DownstreamList[count3]
                                                        fromexists2 = fromfeat in DownstreamList[count2]
                                                        if fromexists1 > 0 and fromexists2 < 1:
                                                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(fromfeat) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(toList[upcount]) + "));"
                                                            rs2.Open(querystring, conn, 1, 3)
                                                            removeEdgeList.append(fromfeat)
                                                        upcount = upcount + 1
                                                        
                                            else: # this is if the user chose the minimum option
                                                if weightList[count2][index1] > weightList[count3][index2]:
                                                    upcount = 0
                                                    for fromfeat in fromList:
                                                        fromexists1 = fromfeat in DownstreamList[count3]
                                                        fromexists2 = fromfeat in DownstreamList[count2]
                                                        if fromexists1 < 1 and fromexists2 > 0 :
                                                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(fromfeat) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(toList[upcount]) + "));"
                                                            rs2.Open(querystring, conn, 1, 3)
                                                            removeEdgeList.append(fromfeat)
                                                        upcount = upcount + 1
                                                else:
                                                    upcount = 0
                                                    for fromfeat in fromList:
                                                        fromexists1 = fromfeat in DownstreamList[count3]
                                                        fromexists2 = fromfeat in DownstreamList[count2]
                                                        if fromexists1 > 0 and fromexists2 < 1 :
                                                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(fromfeat) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(toList[upcount]) + "));"
                                                            rs2.Open(querystring, conn, 1, 3)
                                                            removeEdgeList.append(fromfeat)
                                                        upcount = upcount + 1
                                        count3 = count3 + 1
                                index1 = index1 + 1
                        count2 = count2 + 1                               
                                
            else: # this is if divergent edges have the same outlet edges and one has to be removed
                #gp.AddMessage("Remove from relationships table")
                count2 = 1
                edgeID = DownstreamList[0][0]
                weightValue = sumWeightList[0]
                while count2 <= (listCount - 1):
                    if UserCrit == "Maximum":
                        if weightValue < sumWeightList[count2]:
                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(OrgFrom) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(edgeID) + "));"
                            rs2.Open(querystring, conn, 1, 3)
                            removeEdgeList.append(edgeID)
                            edgeID = DownstreamList[count2][0]
                            weightValue = sumWeightList[count2]
                        else:
                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(OrgFrom) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(DownstreamList[count2][0]) + "));"
                            rs2.Open(querystring, conn, 1, 3)
                            removeEdgeList.append(DownstreamList[count2][0])
                    else:
                        if weightValue > sumWeightList[count2]:
                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(OrgFrom) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(edgeID) + "));"
                            rs2.Open(querystring, conn, 1, 3)
                            removeEdgeList.append(edgeID)
                            edgeID = DownstreamList[count2][0]
                            weightValue = sumWeightList[count2]
                        else:
                            querystring = "DELETE " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat FROM " + ChannelTableName + " WHERE (((" + ChannelTableName + ".fromfeat)=" + str(OrgFrom) + ") AND ((" + ChannelTableName + ".tofeat)=" + str(DownstreamList[count2][0]) + "));"
                            rs2.Open(querystring, conn, 1, 3)
                            removeEdgeList.append(DownstreamList[count2][0])
                    count2 = count2 + 1
            count1 = count1 + 1
        count = count + 1
    outletCountList = ""
    orgoutletCountList = ""
    SumWeightList = ""
    fromList = ""
    toList = ""
    return removeEdgeList
if __name__ == "__main__":
    try:

        InputFC = sys.argv[1]                       # Input Feature Class
        WeightField = sys.argv[2]                   # field that will be used to determine channel
        ChannelTableName = sys.argv[3]              # this is a field that will be populated with 0 and 1s
        UserCrit = sys.argv[4]                      # this determines if the main channel is min or max dist
        #showRemoved = sys.argv[5]                   # if this is checked then a selection set of removed relationships will be displaied

        Path = gp.Describe(InputFC).Path            # Get the full path of the featureclass this includes PGDB name
        FeatureclassPath = Path
        PGDBName = os.path.basename(Path)           # Get the PGDB full name from Featureclasspath
        FullFeatureclassPath = Path
        gp.Workspace = Path                         #set work space = to featureclass path
        
        FeatureclassName = gp.Describe(InputFC).Name
        RelTableName = "relationships"
        # AccField = "shape_length"
        
        # look and see if the table valence exists, if it does then delete it    
        tbs = gp.ListTables(RelTableName)
        tb = tbs.next()
        if tb: # IF ReltableName exists then
            # find name for channel table which is a copy of the relationships table
            # it will have relationships removed to generate main channel through braided channels
            tbs = gp.ListTables(ChannelTableName)
            tb = tbs.next()
            if tb:
                gp.Delete(ChannelTableName)
 
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            gp.AddWarning("Creating main channel table " + ChannelTableName + " in Landscape Network " + Path + " ...")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            gp.copyrows("relationships", ChannelTableName)


            DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + Path
            conn.Open(DSN)

            rs = win32com.client.Dispatch(r'ADODB.Recordset')
            # rs_name = RelTableName
            #querystring = "SELECT " + ChannelTableName + ".fromfeat, Count(" + ChannelTableName + ".fromfeat) AS di_count FROM " + ChannelTableName + " GROUP BY " + ChannelTableName + ".fromfeat HAVING(((Count(" + ChannelTableName + ".fromfeat))>1));"
            #querystring = "SELECT " + ChannelTableName + ".fromfeat, Count(" + ChannelTableName + ".fromfeat) AS di_count FROM " + ChannelTableName + " GROUP BY " + ChannelTableName + ".fromfeat HAVING (((Count(" + ChannelTableName + ".fromfeat))>1)) ORDER BY Min(" + ChannelTableName + ".OBJECTID);"
            querystring = "SELECT " + ChannelTableName + ".fromfeat, Count(" + ChannelTableName + ".fromfeat) AS di_count, Min(" + ChannelTableName + ".OBJECTID) AS [order] FROM " + ChannelTableName + " GROUP BY " + ChannelTableName + ".fromfeat HAVING (((Count(" + ChannelTableName + ".fromfeat))>1)) ORDER BY Min(" + ChannelTableName + ".OBJECTID);"
            gp.AddMessage(querystring)
            rs.Open(querystring, conn, 1) 
            rs.MoveFirst
            gp.AddMessage(" ")
            gp.AddMessage("Finding Braided Stream Channels and Resolving main Channel...")
            gp.AddMessage(" ")
            while not rs.EOF:
                Downstreamlist = [] # this list holds nested list of downstream edges for each divergent stream reach set
                WeighList = [] # this list holds the accumulated weight value for each reach segemnt within the DownstreamList
                fromfeat = rs.Fields.Item("fromfeat").Value
                gp.AddMessage("Evaluating reach: " + str(fromfeat))
                rs1 = win32com.client.Dispatch(r'ADODB.Recordset')

                querystring = "SELECT " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat, " + FeatureclassName + "." + WeightField + " AS weight FROM (" + ChannelTableName + " INNER JOIN " + FeatureclassName + " ON " + ChannelTableName + ".tofeat = " + FeatureclassName + ".rid) INNER JOIN " + ChannelTableName + " AS main_ch_1 ON " + FeatureclassName + ".rid = main_ch_1.fromfeat GROUP BY " + ChannelTableName + ".fromfeat, " + ChannelTableName + ".tofeat, " + FeatureclassName + "." + WeightField + " HAVING (((" + ChannelTableName + ".fromfeat)=" + str(fromfeat) + ") AND ((Min(main_ch_1.OBJECTID))>=" + str(rs.Fields.Item("order").Value) + "));"

                rs1.Cursorlocation = 3
                rs1.Open(querystring, conn, 1, 3)
                rs1.MoveFirst
                if rs1.RecordCount > 1:
                    DownstreamList = [] # this list holds multi list of downstream edges
                    weightList = [] # this list holds multi lists of summed weights of the downstream edges
                    outletList = [] # this list holds multi lists of outlet designation of downstream edges
                    listCount = 0 # keeps track of list appended to main lists
                    while not rs1.EOF:
                        list1 = [] # temp list that will be nested into Downstreamlist with edge ids
                        list2 = [] # temp list that will be nested into weightList with edge weight values
                        list3 = [] # temp list that will be nested into outletList with 1 = outlet and 0 = not outlet
                        list1.append(rs1.Fields.Item("tofeat").Value)
                        #gp.AddMessage("   " + str(rs1.Fields.Item("tofeat").Value))
                        list2.append(rs1.Fields.Item("weight").Value)
                        list3.append(0)
                        count = 0
                        for fid in list1:
                            dummy = GetDownstreamFeatures(conn, list1, list2, list3, fid, ChannelTableName, WeightField, list2[count], UserCrit, count)
                            count = count + 1
                        DownstreamList.append(list1)
                        weightList.append(list2)
                        outletList.append(list3)
                        listCount = listCount + 1
                        rs1.MoveNext()
                if rs1.RecordCount > 1:
                    removeEdgesList = FindLocalChannel(DownstreamList, weightList, outletList, conn, ChannelTableName, UserCrit, listCount, fromfeat)
                    #if len(removeEdgesList) > 0:
                        #for rid in removeEdgesList:
                        #string = "rid = " + str(rid)
                            #gp.AddError("         " + str(rid))
                            #gp.SelectLayerByAttribute(FeatureclassName, "ADD_TO_SELECTION", string)
                rs1.Close()
                rs1 = "nothing"
                rs.MoveNext()

            rs.Close()
            #rs1.Close()
            rs = "Nothing"
            #rs1 = "nothing"
            # add edges to remove relationships to selection set
            gp.AddMessage("  ")
            gp.AddMessage("  ")
            gp.AddWarning("Finished Fining Main Channels Through Braided Channels")
            gp.AddMessage("  ")
            gp.AddMessage("  ")
            gp.AddMessage("  ")
        else:
            gp.AddMessage("Relationship table doesn't exist")
            

    except:
        print gp.GetMessages(0)
        print conn.GetMessages()
    
    