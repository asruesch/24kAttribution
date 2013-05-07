import arcgisscripting, arcpy, sys, string, os, re, time, math #win32com.client
from time import *
from decimal import Decimal

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create(9.2)


# ******************************************************
# ********    FUNCTIONS   ******************************
# ******************************************************
# This function calculates distance between points
def CalcDist(startx, starty, tox, toy):
    a = (starty - toy)
    b = (startx - tox)
    dist = math.hypot(a,b) 
    return dist
# This Function reselect out an edge with a fid = to fid and breakes it up into parts
# the parts are evaluated to find the nearest vertex and then calculate distance downstream
def IsOnLine(fromx, fromy, tox, toy, pntx, pnty):
    r = CalcDist(fromx, fromy, tox, toy) # distance of segment between to and from vertices
    rprime = CalcDist(fromx, fromy, pntx, pnty) # distance between from vertex and new point coords 

#-----------------------
# These lines were added to make sure a 1 is returned if a point sits exactly on a vertex
# rounding errors were causing a 0 to be returned in the next two lines when rprime
# and r are equal
    if abs(rprime - r) < 0.001: # if new site sites on the to vertex....
        return 1
##    if abs(0-rprime) < 0.001: # second check. if new site sits on the from vertex
##        return 1
#------------------------
    if rprime > r:
        return 0
  
    ydiff = abs(fromy - toy)
    yprimediff = abs(fromy - pnty)
    
    ratio = round(math.sin(ydiff / r), 2)
    ratioprime = round(math.sin(yprimediff / rprime), 2)
    if ratio == ratioprime:
        return 1
    else:
        return 0
def DynamicSplit3(fid, xcoord, ycoord, edgeFCName):
    rows = gp.searchCursor(edgeFCName, "rid = " + str(fid))
    row = rows.Next()
    feature = row.shape

##    print "Edge RID = " + str(fid)
##    if fid == 47:
##        print "rid = 47"
        
    fLength = feature.Length # this is the length of an edge that a point lands on
    x = 0
    pointfound = 0
    totaldist = 0
    pointdist = 0
    vertexid = 0
    while x < feature.PartCount: # loop through all points that make up the edge
        PTarray = feature.GetPart(x)
        PTarray.Reset()
        pnt = PTarray.Next()
        count = 0
        mindist = 999999 # set a high min dist
        while pnt:
            if count > 0:
                dist2 = CalcDist(fromx, fromy, pnt.x, pnt.y)
                dist1 = CalcDist(xcoord, ycoord, pnt.x, pnt.y) # this is the distance from vertex to point
                if dist1 < mindist:
                    if IsOnLine(fromx, fromy, pnt.x, pnt.y, xcoord, ycoord) == 1: # check to see if ppoint falls on line
                        mindist = dist1
                        fromdist = CalcDist(fromx, fromy, xcoord, ycoord) # find the distance from the from point 
                        todist = CalcDist(pnt.x, pnt.y, xcoord, ycoord) # find the distance from the to point
##                        if fid == 29:
##                            print "IsOnLine returned 1"
##                            print "     count = " + str(x)
##                            print "     fromdist = " + str(fromdist)
##                            print "     todist = " + str(todist)
##                            print "     dist2 = " + str(dist2)
##                            print "     totaldist = " + str(totaldist)
##                            
                        if fromdist < todist: # if from point is closer than add distance
                            pointdist = totaldist + fromdist
                        else: # if the topoint is closer add line seg distance - to distance
                            pointdist = totaldist + (dist2 - todist)
            else:
                dist2 = 0
            totaldist = totaldist + dist2
##            if fid == 29:
##                print "total distance = " + str(totaldist)
            fromx = pnt.x # this sets the current point to a from point for the next iteration
            fromy = pnt.y
            count = count + 1
            pnt = PTarray.Next()
        x = x + 1

########
# the pointdist is set to negative and so it makes the total length (length) greater than the total length of the segment (fLength)
##########
        length = (fLength - pointdist) # this sets the ratio so that it will represent the distance from the point to the end of the edge
        #gp.AddMessage("length " + str(length) + " flength " + str(fLength))
       
        if fLength == 0:
            ratio = 1
        else:
            ratio = float(length / fLength)
        if ratio < .0001:
            ratio = .001

##        if fid == 29:
##            print "length = " + str(totaldist)
##            print "pointdist = " + str(pointdist)
##            print "ratio " + str(fid) + " = " + str(ratio)
            
    return ratio # return the ratio a point falls from the end of an edge
# **********************************************************
# *********   MAIN Routine   *******************************
# **********************************************************
if __name__ == "__main__":
    try:

##        SamplePTS = r"d:/projects/nceas/gisdata/lsns/LSN031811/lsn2/preds1km.shp"  # Sample points to snap to network
##        EdgeNetwork = r"d:/projects/nceas/gisdata/lsns/LSN031811/lsn3/lsn3.mdb/edges" # Network to snap sample points to
##        OutPutFC = r"D:/projects/nceas/gisdata/lsns/LSN031811/lsn3/lsn3.mdb/preds1km" # Output snapped points name and location -> this should be a featureclass in a PGDB
##        SearchLength = 75 # max search distance


#        # Input Sampe Points and Edge Netwok Feature classes
        SamplePTS = sys.argv[1]  # Sample points to snap to network
        EdgeNetwork = sys.argv[2] # Network to snap sample points to
        OutPutFC = sys.argv[3] # Output snapped points name and location -> this should be a featureclass in a PGDB
        SearchLength = sys.argv[4] # max search distance

        samplePTS = gp.Describe(SamplePTS).Path + "\\" + gp.Describe(SamplePTS).Name
        EdgeNetwork = gp.Describe(EdgeNetwork).Path + "\\" + gp.Describe(EdgeNetwork).Name
        PGDBPath = gp.Describe(EdgeNetwork).Path # Get the path to the personal geodatabase
        ShapeFileWorkspace = gp.Describe(SamplePTS).Path # Get the path of the input sample point feature class
        SampleFCName = gp.Describe(SamplePTS).Name # Get the name of the input sampel point feature class
        edgesFCName = gp.Describe(EdgeNetwork).Name # Get the name of the edge feature class
        List = os.path.split(OutPutFC) # Popoulate a list with the path and name of the output point featureclass
        outputFCName = List[1] # get the name of the output sample point featureclass

        gp.workspace = PGDBPath
        # make sure field calculated in the NEAR command are not present when the command is issued
        gp.AddMessage("  ")
        gp.AddMessage("Running NEAR Command...")
        gp.AddMessage("   ")
        # Run the NEAR command to find the closest edge
        gp.Near_analysis(SamplePTS, EdgeNetwork , SearchLength, "LOCATION", "ANGLE")
        gp.AddMessage("Evaluating edges...")
        gp.AddMessage("  ")
        #set up search cursor to move through sample point feature class
        #to extract infromation created with NEAR command

        print "part 1"
        gp.AddMessage("Building " + outputFCName + " Featureclass")
        gp.AddMessage("  ")
        # create a featureclass for the new adjusted points
        # gp.CreateFeatureclass(PGDBPath, os.path.basename(OutPutFC), "Point", SamplePTS)
        if gp.Exists("C:/TEMP/snaptemp.shp"):
            gp.Delete("C:/TEMP/snaptemp.shp")
        gp.CreateFeatureclass("C:/TEMP", "snaptemp.shp", "Point", SamplePTS)
        # check it see if nessary fields exist 
        if not gp.listfields(samplePTS, "rid").Next():
            gp.AddField("C:/TEMP/snaptemp.shp", "rid","long")
        if not gp.listfields(samplePTS, "ratio").Next():
            gp.AddField("C:/TEMP/snaptemp.shp", "ratio", "double")
        pointCur = gp.InsertCursor("C:/TEMP/snaptemp.shp")
        # create the array and point objects neede to create a feature
        pointPNT = gp.CreateObject("Point")
        rows = gp.SearchCursor(SamplePTS)
        row = rows.Next()
        gp.AddMessage("Creating Snaped Points Featureclass...")
        gp.AddMessage("  ")

        print "part 2"        
        while row:
            FID = row.near_fid
            print "starting FID " + str(FID)

##            if FID == 48:
##                print "fid = 48"
            xcoord = row.near_x
            ycoord = row.near_y
            newFeature = pointCur.NewRow() # create a new row to insert the feature into
            if FID <> -1:
                FID = FID - 1
                ratio = DynamicSplit3(FID, xcoord, ycoord, EdgeNetwork)
                pointFields = gp.listfields(samplePTS)
                pointField = pointFields.Next()
                count = 1
                #gp.AddMessage("populating fields")
                while pointField: # populate fields input point feature class attributres
                    if count > 3:
                        if row.GetValue(pointField.Name) <> None:
                            newFeature.SetValue(pointField.Name, row.GetValue(pointField.Name))
                    count = count + 1
                    pointField = pointFields.Next()
                #gp.AddMessage("test")

                print "new feature set value " + str(FID)                
                newFeature.rid = FID
                newFeature.ratio = ratio
                pointPNT.id = count
                pointPNT.x = float(xcoord)
                pointPNT.y = float(ycoord)
                newFeature.shape = pointPNT #set the geometery of the new feature to the array of points
                pointCur.InsertRow(newFeature)
                print "set new feature FID " + str(FID)
                count = count + 1
            row = rows.Next()
        # Copy the edges shape file into the geodatabase
        print "part 3"
        del row
        del rows
        del pointCur
        del pointPNT
        gp.CopyFeatures("C:/TEMP/snaptemp.shp", PGDBPath + "/" + outputFCName )
        # gp.Delete("C:/TEMP/snaptemp.shp")
        print "part 4"
        gp.AddMessage("  ")
        gp.AddMessage("  ")
        gp.AddWarning("Finished Snap Points to Landscape Network Edges")
        print "Finished Snap Points to Landscape Network Edges"
        gp.AddMessage("  ")
        gp.AddMessage("  ")
    except:
        print "Did not Snap Points to Landscape Network Edges"
        if gp.Exists("C:/TEMP/snaptemp.shp"):
            gp.Delete("C:/TEMP/snaptemp.shp")
        gp.GetMessages()
