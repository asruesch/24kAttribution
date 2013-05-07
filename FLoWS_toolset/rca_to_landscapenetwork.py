import arcgisscripting, sys, string, os, re, time #win32com.client
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()



def LookForEdge(ToFeatGT, FromFeatGT, NewFromFeatList, NewToFeatList, FID):
    exists = FID in ToFeatGT
    if exists == 1:
        while exists == 1:
            #gp.AddMessage("  " + str(FID))
            ind = ToFeatGT.index(FID)
            exists2 = FromFeatGT[ind] in NewToFeatList
            if exists2 == 1:
                #gp.AddError("    Inserting records")
                ind2 = NewToFeatList.index(FromFeatGT[ind])
                NewFromFeatList.insert((ind2), FromFeatGT[ind])
                NewToFeatList.insert((ind2), ToFeatGT[ind])
            else:
                #gp.AddWarning("   add records")
                NewFromFeatList.append(FromFeatGT[ind])
                NewToFeatList.append(ToFeatGT[ind])
            #gp.AddMessage("  " + str(FromFeatGT[ind]) + " " + str(ToFeatGT[ind]))
            del FromFeatGT[ind]
            del ToFeatGT[ind]
            exists = FID in ToFeatGT    
    return 1

def uniqueFeature(uniqueFeatureList, FID):
    exists = FID in uniqueFeatureList
    if exists == 0:
        uniqueFeatureList.append(FID)
    return 1

#Main Function
if __name__ == "__main__":
    # Table which was produced by Check Geometry tool
    Reachfeatureclass = sys.argv[1] #"C:/temp/hca-data/fraser_reaches.shp"
    JoinField = sys.argv[2] # this field is used to join edge and RCA features
    HCAfeatureclass = sys.argv[3] #"c:/temp/hca-data/hca.shp"
    geoDatabase = sys.argv[4] # output landscape network name and path
    pointxyTable = "nodexy"
    indexTable = "arcindex"
    # geoDatabase = "C:/temp/hca-data/testgeodb.mdb

    #Path = gp.Describe(geoDatabase).Path
    #PGDBName = gp.Describe(geoDatabase).Name
    
    Path = os.path.dirname(geoDatabase)         # Get the full path of the featureclass this includes PGDB name
    PGDBName = os.path.basename(geoDatabase)    # Get the name of the output geodatabase
    
    # Create some variables
    dict = {}
    query = ""
    fieldName = ""
    # gp.workspace = Path
    gp.overwriteoutput

    # gp.workspace = Path
    # Create Geodatabase and tables nessary to make a geonetwork
    # create Grodatabase
    gp.AddMessage(" ")
    gp.AddMessage("Creating Landscape Network " + str(PGDBName) + "....")
    gp.AddMessage(" ")
    gp.CreatePersonalGDB(Path, PGDBName)

    gp.AddMessage(" ")
    gp.AddMessage("     Creating Landscape Tables....")
    gp.AddMessage(" ")
    # create Blanktable in Geodatabase to be filled with point ID, XCoord, and YCoord.  This is
    # nessary to create a point featureclass from to coords.
    gp.CreateTable(geoDatabase, "nodexy")
    gp.AddField(geoDatabase + "/nodexy","pointid","long","9")
    gp.AddField(geoDatabase + "/nodexy","xcoord","double","12")
    gp.AddField(geoDatabase + "/nodexy","ycoord","double","12")

    # Create blank table in Geodatabase to be filled with node edge relationsships.
    gp.CreateTable(geoDatabase, "noderelationships")
    gp.AddField(geoDatabase + "/noderelationships", "rid", "long", "9")
    gp.AddField(geoDatabase + "/noderelationships", "fromnode", "long", "9")
    gp.AddField(geoDatabase + "/noderelationships", "tonode", "long", "9")
    
    # Create relationships table that holds feature to feature relationships

    gp.CreateTable(geoDatabase, "relationships")
    gp.AddField(geoDatabase + "/relationships", "fromfeat", "long", "9")
    gp.AddField(geoDatabase + "/relationships", "tofeat", "long", "9")

    #Loop through the table using a cursor
    rows = gp.searchCursor(Reachfeatureclass)
    row = rows.Next()

    #Set up Insert cursor for point x y table
    Nodexyrows = gp.InsertCursor(geoDatabase + "/nodexy")
    Nodexyrow = Nodexyrows.NewRow()

    PntID = 0
    gp.AddMessage(" ")
    gp.AddMessage("     Building Node/Edge Relationships....")
    gp.AddMessage(" ")
    while row:
        # Get the class (feature class) for that row, as well as the Feature ID
        FID = row.GetValue("fid")
        feature = row.shape
        FromPoint = feature.FirstPoint
        ToPoint = feature.LastPoint
        if PntID == 0:
            #print "First record added"
            PntIDList = [PntID] # add number to node point list
            CoordList = [FromPoint] # get xy coord string
            FromPointIDList = [PntID] # set frompoint id value
            coords = FromPoint.split(" ") # split coord string in x and y values
            Nodexyrow.pointid = PntID # add node id to table
            Nodexyrow.xcoord = coords[0] # add x value to table
            Nodexyrow.ycoord = coords[1] # add y value to table
            Nodexyrows.InsertRow(Nodexyrow)
            PntID = PntID + 1 # add one to point ID for tonode id value
            PntIDlist = PntIDList.append(PntID)
            CoordList.append(ToPoint)
            FeatureList = [FID]
            ToPointIDList = [PntID]
            coords = ToPoint.split(" ")
            Nodexyrow.pointid = PntID
            Nodexyrow.xcoord = coords[0]
            Nodexyrow.ycoord = coords[1]
            Nodexyrows.InsertRow(Nodexyrow)
        else:
            fromInd = FromPoint in CoordList        # returns 1 if exists 0 if not
            toInd = ToPoint in CoordList            # returns 1 if exists 0 if not
            FeatureList.append(FID)
            
            if fromInd > 0 and toInd == 0:          #Frompoint coord exists in Coordlist and ToPoint doesn't, so add ToPoint to CoordList  
                #print "Adding ToPoint Coordinates"
                PntIDList.append(PntID)
                CoordList.append(ToPoint)
                ind = CoordList.index(FromPoint)
                PointID = PntIDList[ind]
                FromPointIDList.append(PointID)
                ToPointIDList.append(PntID)
                # Insert into table
                coords = ToPoint.split(" ")
                Nodexyrow.pointid = PntID
                Nodexyrow.xcoord = coords[0]
                Nodexyrow.ycoord = coords[1]
                Nodexyrows.InsertRow(Nodexyrow)

            elif fromInd == 0 and toInd > 0:
                #print "Adding FromPoint Coordinates"
                PntIDList.append(PntID)
                CoordList.append(FromPoint)
                ind = CoordList.index(ToPoint)
                #print ind
                PointID = PntIDList[ind]
                FromPointIDList.append(PntID)
                ToPointIDList.append(PointID)
                # Insert into table
                coords = FromPoint.split(" ")
                Nodexyrow.pointid = PntID
                Nodexyrow.xcoord = coords[0]
                Nodexyrow.ycoord = coords[1]
                Nodexyrows.InsertRow(Nodexyrow)
            
            elif fromInd == 0 and toInd == 0:
                #print "Adding both coordinates"
                PntIDList.append(PntID)
                CoordList.append(FromPoint)
                FromPointIDList.append(PntID)
                # Insert into table
                coords = FromPoint.split(" ")
                Nodexyrow.pointid = PntID
                Nodexyrow.xcoord = coords[0]
                Nodexyrow.ycoord = coords[1]
                Nodexyrows.InsertRow(Nodexyrow)
                PntID = PntID + 1
                PntIDList.append(PntID)
                CoordList.append(ToPoint)
                ToPointIDList.append(PntID)
                # Insert into table
                coords = ToPoint.split(" ")
                Nodexyrow.pointid = PntID
                Nodexyrow.xcoord = coords[0]
                Nodexyrow.ycoord = coords[1]
                Nodexyrows.InsertRow(Nodexyrow)

            elif fromInd > 0 and toInd > 0:
                #print "Not adding coordinates"
                ind = CoordList.index(ToPoint)
                PointID = PntIDList[ind]
                ToPointIDList.append(PointID)
                ind = CoordList.index(FromPoint)
                PointID = PntIDList[ind]
                FromPointIDList.append(PointID)

        PntID = PntID + 1    
        row = rows.Next()
        Nodexyrow = Nodexyrows.NewRow()

    gp.AddMessage("     Populating Relationship Tables....")
    gp.AddMessage(" ")
    #Setup Insert cursor to populate index table with where a features relationships are located in the relationships table
    # Setup Insert cursor to populate relationships table with feature to feature relationships
    featureRelrows = gp.InsertCursor(geoDatabase + "/relationships")
    featureRelrow = featureRelrows.NewRow()

    startIndex = 0 # this is used to get the FID in the main loop
    GTfound = 0

    #Set up Inset cursor for noderelationship table
    Noderows = gp.InsertCursor(geoDatabase + "/noderelationships")

    #loop through all ToPointIDs in list and look for a coresponding FromNode
    # once, a coresponding fromnode is found populate relationships table
    # with each iteration of the ToPointIDList populate index table
    nodeIDindex = 0
    edgeID = 0
    gp.AddMessage("     Building Edge (Hydro) Network Features.....")
    FromFeatGT = [] # list of from Features 
    ToFeatGT = [] # list of to features is matches the from feature list
    uniqueFeatureList = [] # list on unique feature ids this is used to find sink features
    for ToFeature in ToPointIDList:
        # populate noderelationships table
        Noderow = Noderows.NewRow()
        Noderow.rid = edgeID
        dummy = uniqueFeature(uniqueFeatureList, edgeID) # this function queries if this feature exists in list if it doesn't add id
        Noderow.fromnode = FromPointIDList[nodeIDindex]
        Noderow.tonode = ToFeature
        Noderows.InsertRow(Noderow)
        forwardIndex  = 0 # this is the location in the list that fromnode and tondoe are equal, and is used to get the coresponding FID
        for FromFeature in FromPointIDList:
            if FromFeature == ToFeature:
                FromFeatGT.append(FeatureList[startIndex])
                ToFeatGT.append(FeatureList[forwardIndex])
            forwardIndex = forwardIndex + 1
        nodeIDindex = nodeIDindex + 1
        edgeID = edgeID + 1
        startIndex = startIndex + 1
        
    # this loop get all sink features in edge feature class to be used to calculate up stream edges
    SinkList = [] # list of all sink features
    for FID in uniqueFeatureList:
        exists = FID in FromFeatGT
        if exists == 0:
            SinkList.append(FID)
            
    uniqueFeatureList = []  # set uniqueFeatureList to nothing
    gp.AddMessage(" ")
    gp.AddMessage("     Sorting Edge Relationship Table Downstream.....")
    gp.AddMessage(" ")
    # this loop start a all Sink features in the SinkList and builds to from list working up stream to build a sorted downstream list
    NewFromFeatList = [] # this is a new list of from features sorted upstream
    NewToFeatList = [] # this is a new list of to features sortes upstream
    sinkcount = 1
    for SinkFID in SinkList:
        #gp.AddError("Sinkcount = " + str(sinkcount) + " and Sinkfeature ID = " + str(SinkFID))
        exists = SinkFID in ToFeatGT
        if exists == 1:
            #gp.AddMessage("Sinkcount = " + str(sinkcount) + " and Sinkfeature ID = " + str(SinkFID))
            if sinkcount == 1:
                while exists == 1:
                    ind = ToFeatGT.index(SinkFID)
                    #gp.AddWarning(str(SinkFID) + " " + str(FromFeatGT[ind]))
                    NewFromFeatList.append(FromFeatGT[ind])
                    NewToFeatList.append(ToFeatGT[ind])
                    del FromFeatGT[ind]
                    del ToFeatGT[ind]
                    exists = SinkFID in ToFeatGT
                for FID in NewFromFeatList:
                    #gp.AddMessage(str(FID))
                    dummy = LookForEdge(ToFeatGT, FromFeatGT, NewFromFeatList, NewToFeatList, FID) # this function gets upstream edges from a given FID
            else:
                tempFrom = []
                tempTo = []
                count = 1
                while exists == 1:
                    #gp.AddMessage(str(tempFrom) + " " + str(count))
                    ind = ToFeatGT.index(SinkFID)
                    #gp.AddWarning(str(FromFeatGT[ind]) + " " + str(ToFeatGT[ind]))
                    tempFrom.append(FromFeatGT[ind])
                    tempTo.append(ToFeatGT[ind])
                    del FromFeatGT[ind]
                    del ToFeatGT[ind]
                    exists = SinkFID in ToFeatGT
                    count = count + 1
                for FID in tempFrom:
                    #gp.AddMessage("   " + str(FID))
                    dummy = LookForEdge(ToFeatGT, FromFeatGT, tempFrom, tempTo, FID) # this function gets upstream edges from a given FID                    
        
            if sinkcount <> 1:
                #gp.AddMessage("    " + str(sinkcount))
                #gp.AddMessage(str(tempFrom))
                lastIndex = (len(tempFrom) - 1)
                exists = tempFrom[lastIndex] in NewToFeatList
                exists2 = tempFrom[lastIndex] in NewFromFeatList
                if exists == 1:
                    #gp.AddMessage("     " + str(tempFrom[lastIndex]) + " exists")
                    #index = NewToFeatList.index(tempFrom[lastIndex])
                    x = len(tempFrom) - 1
                    while x > -1:
                        exists = tempFrom[x] in NewToFeatList
                        if exists == 1: # this will place stream reaches in correct downstream order
                            index = NewToFeatList.index(tempFrom[x])
                        NewFromFeatList.insert(index, tempFrom[x])
                        NewToFeatList.insert(index, tempTo[x])
                        x = x - 1
                elif exists2 == 1:
                    #gp.AddMessage("     " + str(tempFrom[lastIndex]) + " exists")
                    #index = NewToFeatList.index(tempFrom[lastIndex])
                    x = len(tempFrom) - 1
                    while x > -1:
                        exists = tempFrom[x] in NewFromFeatList
                        if exists == 1: # this will place stream reaches in correct downstream order
                            index = NewFromFeatList.index(tempFrom[x])
                        else:
                            index = 0
                        NewFromFeatList.insert(index, tempFrom[x])
                        NewToFeatList.insert(index, tempTo[x])
                        x = x - 1                   
                else:
                    indexcount = 0
                    #gp.AddMessage("     " + str(tempFrom[lastIndex]) + " doesn't exist")
                    for fid in tempFrom:
                        NewFromFeatList.append(fid)
                        NewToFeatList.append(tempTo[indexcount])
                        indexcount = indexcount + 1

        sinkcount = sinkcount + 1
    tempFrom = "nothing"
    tempTo = "nothing"
    gp.AddMessage("     Linking Relationship Tables to Features")
    gp.AddMessage(" ")
    # go through NewFeatLists from the bottom up to sort downstream
    x = len(NewFromFeatList) - 1
    while x > -1:
        featureRelrow = featureRelrows.NewRow()
        featureRelrow.fromfeat = NewFromFeatList[x]
        featureRelrow.tofeat = NewToFeatList[x]
        featureRelrows.InsertRow(featureRelrow)
        x = x - 1


    #Create point layer from x,y table
    gp.workspace = geoDatabase
    # make Event Layer out of x,y table
    gp.MakeXYEventLayer(geoDatabase + "/nodexy", "xcoord" , "ycoord", "nodes.lyr")
    # create a temp. featurelayer out of layer file
    gp.MakeFeatureLayer("nodes.lyr","nodes")
    # Copy Nodes, Reach input, and hCA layers into new featureclasses in GeoDataBase
    gp.CopyFeatures("nodes", geoDatabase + "/nodes")
    # Copy the reaches shape file into the geodatabase
    gp.CopyFeatures(Reachfeatureclass, geoDatabase + "/edges")
    # Copy the hca shpaefile into the geodatabase
    gp.CopyFeatures(HCAfeatureclass, geoDatabase + "/rca")

    gp.Workspace = geoDatabase
    gp.AddMessage(" ")
    #gp.AddWarning(gp.Workspace)
    gp.AddMessage("Building Feature Classes ...")
    if not gp.ListFields("rca", "rid").Next(): gp.AddField("rca", "rid", "long", "12", "12")
    #gp.AddField("edges", "rid","long", "12", "12")
    # add RID and find the OID field 
    if not gp.ListFields("edges", "rid").Next():
        gp.AddField("edges", "rid","long", "12", "12")
    if gp.ListFields("edges", "*", "OID").Next():
        OIDField = gp.ListFields("edges", "*", "OID").Next()
        gp.CalculateField("edges", "rid", "[" + str(OIDField.Name) + "] - 1")
        
    edgerows = gp.SearchCursor("edges")
    edgerow = edgerows.Next()
    while edgerow:
        # Create update cursor for feature class
        rcarows = gp.UpdateCursor("rca", "[GRIDCODE] = " + str(edgerow.GetValue(JoinField)))
        rcarow = rcarows.Next()
        while rcarow:
            rcarow.rid = long(edgerow.rid)
            rcarows.UpdateRow(rcarow)
            rcarow = rcarows.Next()
        edgerow = edgerows.Next()
    
    gp.AddField("rca", "reachid", "long", "12", "12")
    gp.CalculateField("rca", "reachid", "[gridcode]")
    gp.deletefield ("rca", "gridcode")

    
    gp.AddMessage("   ")
    gp.AddMessage("   ")
    gp.AddWarning("FINISHED RCAs to Landscape Network Script")
    gp.AddMessage("   ")
    gp.AddMessage("   ")