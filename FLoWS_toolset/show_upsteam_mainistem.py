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
def AccumulateValues(RidWeightList, RelationshipList):
    index = 0
    #gp.AddMessage("1")
    for fromfeat in RelationshipList[0]:
        tofeat = RelationshipList[1][index]
        fromind = RidWeightList[0].index(fromfeat)
        toind = RidWeightList[0].index(tofeat)
        RidWeightList[1][toind] = RidWeightList[1][toind] + RidWeightList[1][fromind]
        index = index + 1
    return 1
def GetupstreamFeatures(conn, ridList, id, FeatureclassName, WeightItem, RidWeightList, RelationshipList):
    rs = win32com.client.Dispatch(r'ADODB.Recordset')
    querystring = "SELECT relationships.fromfeat, relationships.tofeat, " + FeatureclassName + "." + WeightItem + " AS weight FROM relationships INNER JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid WHERE (((relationships.tofeat)=" + str(rid) + "));"
    rs.Cursorlocation = 3
    rs.Open(querystring, conn, 1, 3)
    rs.MoveFirst
    if rs.RecordCount > 0:
        while not rs.EOF:
            exists = rs.Fields.Item("fromfeat").Value in ridList
            if exists == 0:
                # add items to RidWeightList
                exists2 = rs.Fields.Item("fromfeat").Value in RidWeightList[0]
                if exists2 == 0:
                    RidWeightList[0].append(rs.Fields.Item("fromfeat").Value)
                    RidWeightList[1].append(rs.Fields.Item("weight").Value)
                #add item to ridlist
                ridList.append(rs.Fields.Item("fromfeat").Value)
                #add items to relationshipList
                RelationshipList[0].append(rs.Fields.Item("fromfeat").Value)
                RelationshipList[1].append(rs.Fields.Item("tofeat").Value)
            rs.MoveNext()
    rs = "Nothing"
    return 1

def FindMainStem(SinkFID, RelationshipList, RidWeightList, MainStemList):
    tempFeatList = []
    tempValueList = []
    count = 0
    exists3 = 0
    tempIndex = 0
    maxTribValue = -1
    exists = SinkFID in RidWeightList[0]
    if exists == 1:
        ind = RidWeightList[0].index(SinkFID)
        tempFeatList.append(SinkFID)
        tempValueList.append(RidWeightList[1][ind])
    exists = SinkFID in RelationshipList[1]
    while exists == 1: # while SinkFID exists in the tofeature of the relationshiplist add the fromfeature id to the list
        ind = RelationshipList[1][tempIndex:].index(SinkFID)
        exists2 = RelationshipList[0][ind] in tempFeatList
        if exists2 == 0: #If featureid is not in the list already
            exists3 = RelationshipList[0][ind] in RidWeightList[0]
            if exists3 == 1: # if the feature id is in the RidWeightList add feture and weight value to lists
                ind2 = RidWeightList[0].index(RelationshipList[0][ind + tempIndex])
                #gp.AddMessage(str(maxTribValue) + " " + str(RidWeightList[1][ind2]))
                if maxTribValue <= RidWeightList[1][ind2]:
                    maxTrib = RelationshipList[0][ind + tempIndex]
                    maxTribValue = RidWeightList[1][ind2]                       
                    maxIndex = ind + tempIndex
                    maxIndex2 = ind2
            if tempIndex == 0:
                tempIndex = ind + 1
            else:
                tempIndex = tempIndex + 1
            exists = SinkFID in RelationshipList[1][tempIndex:]
            count = count + 1
    if exists3 == 1:
        exists = RelationshipList[0][maxIndex] in tempFeatList
        if exists == 0:
            tempFeatList.append(RelationshipList[0][maxIndex])
            tempValueList.append(RidWeightList[1][maxIndex2])
        # this for loop builds on the elements already added to it in the loop above it keeps building until all elements in a drainage have been added
        for featID in tempFeatList:
            LookForLargestUpstreamFeature(RelationshipList, RidWeightList, tempFeatList, tempValueList, featID) # this function finds upstream features given a featID (TOFEAT)
        # nest features and their values lists into a temp list that is nested in the drainageList
        tempList = [] # this list will hold tempFeatList and tempValueList
        tempList.append(tempFeatList)
        tempList.append(tempValueList)
        MainStemList.append(tempList) # each element in the drainageList hold a nested drainage list
        tempList = []
        tempFeatList = []
        tempValueList = []
    return 1
def LookForLargestUpstreamFeature(RelationshipList, RidWeightList, tempFeatList, tempValueList, FID):
    exists = FID in RelationshipList[1]
    exists3 = 0
    count = 0
    tempIndex = 0
    maxTribValue = -1
    if exists == 1:
        while exists == 1:
            ind = RelationshipList[1][tempIndex:].index(FID)
            exists3 = RelationshipList[0][ind] in RidWeightList[0]
            if exists3 == 1: # if the feature id is in the RidWeightList add feture and weight value to lists
                ind2 = RidWeightList[0].index(RelationshipList[0][ind + tempIndex])
                if maxTribValue <= RidWeightList[1][ind2]:
                    maxTrib = RelationshipList[0][ind + tempIndex]
                    maxTribValue = RidWeightList[1][ind2]                    
                    maxIndex = ind + tempIndex
                    maxIndex2 = ind2
                        
            if tempIndex == 0:
                tempIndex = ind + 1
            else:
                tempIndex = tempIndex + 1
            exists = FID in RelationshipList[1][tempIndex:]
            count = count + 1
    if exists3 == 1:
        exists = RelationshipList[0][maxIndex] in tempFeatList
        if exists == 0:
            tempFeatList.append(RelationshipList[0][maxIndex])
            tempValueList.append(RidWeightList[1][maxIndex2])
            #del RelationshipList[0][maxIndex]
            #del RelationshipList[1][maxIndex]
            #del RidWeightList[0][maxIndex2]
            #del RidWeightList[1][maxIndex2]
    return 1
if __name__ == "__main__":

    InputFC = sys.argv[1]   # Input Feature Class
    WeightItem = sys.argv[2] # user defined item associated to input feature class   
    Path = gp.Describe(InputFC).Path    # Get the full path of the featureclass this includes PGDB name
    PGDBName = os.path.basename(Path)                               # Get the PGDB full name from Featureclasspath
    
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

        ridList = [] # this list holds rid of selected features
        weightList = [] # this list holds a a user-defined weight value that Corresponds to a rid
        rows = gp.SearchCursor(FeatureclassName) # this search cursor is to loop through all points and get attributes
        sinkList = [] # this is used to find value above selected features or called sink value
        tempList = [] # this is a temp list that will hold rids
        row = rows.Next()
        gp.AddMessage(" ")
        gp.AddMessage("Getting Selected Features....")
        gp.AddMessage(" ")
        count = 0
        while row: # Loop through the features selected by the search query
            ridList.append(row.GetValue("rid"))
            weightList.append(row.GetValue(WeightItem))
            sinkList.append(row.GetValue("rid"))
            tempList.append(row.GetValue("rid"))
            count = count + 1
            row = rows.Next()
        gp.AddWarning(str(count) + " Selected features being processed.  If this is too many, hit Cancel.")
        gp.AddMessage(" ")
        RidWeightList = [] # this list hold rids and weight value
        RidWeightList.append(tempList)
        RidWeightList.append(weightList)
        weightList = [] # set list to equal nothing

        #create relationshipList
        RelationshipList = []
        list1 = []
        list2 = []
        RelationshipList.append(list1)
        RelationshipList.append(list2)
        gp.AddMessage("Getting Upstream Features....")
        gp.AddMessage(" ")
        for rid in ridList:
            rs = win32com.client.Dispatch(r'ADODB.Recordset')
            querystring = "SELECT relationships.fromfeat, relationships.tofeat, " + FeatureclassName + "." + WeightItem + " AS weight FROM relationships INNER JOIN " + FeatureclassName + " ON relationships.fromfeat = " + FeatureclassName + ".rid WHERE (((relationships.tofeat)=" + str(rid) + "));"
            rs.Cursorlocation = 3
            rs.Open(querystring, conn, 1, 3)
            rs.MoveFirst
            if rs.RecordCount > 0:
                while not rs.EOF:
                    exists = rs.Fields.Item("fromfeat").Value in ridList
                    if exists == 0:
                        # add items to RidWeightList
                        exists2 = rs.Fields.Item("fromfeat").Value in RidWeightList[0]
                        if exists2 == 0:
                            RidWeightList[0].append(rs.Fields.Item("fromfeat").Value)
                            RidWeightList[1].append(rs.Fields.Item("weight").Value)
                        #add item to ridlist
                        ridList.append(rs.Fields.Item("fromfeat").Value)
                        #add items to relationshipList
                        RelationshipList[0].append(rs.Fields.Item("fromfeat").Value)
                        RelationshipList[1].append(rs.Fields.Item("tofeat").Value)
                        dummy = GetupstreamFeatures(conn, ridList, rs.Fields.Item("fromfeat").Value, FeatureclassName, WeightItem, RidWeightList, RelationshipList)
                    rs.MoveNext()

        conn.Close()
        #gp.AddMessage(str(RelationshipList))
        RelationshipList[0].reverse()
        RelationshipList[1].reverse()
        #gp.AddMessage(" ")
        #gp.AddMessage(str(RelationshipList))
        #gp.AddMessage(" ")
        #gp.AddMessage(str(RidWeightList))
        gp.AddMessage("Accumulating values....")
        gp.AddMessage(" ")
        dummy = AccumulateValues(RidWeightList, RelationshipList)
        #gp.AddMessage(str(RidWeightList))
        gp.AddMessage("Finding Main stem....")
        gp.AddMessage(" ")
        #Go through selected features and find main stem above each
        MainStemList = [] #this list will hold main stem features above selected features
        for SinkFID in sinkList:
            dummy = FindMainStem(SinkFID, RelationshipList, RidWeightList, MainStemList)
        gp.AddMessage("Adding Main Stem Features To Selection Set....")
        for ridList2 in MainStemList:
            for rid in ridList2[0]:
                #gp.AddMessage(str(rid))
                string = "rid = " + str(rid)
                #gp.AddMessage(string)
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

    