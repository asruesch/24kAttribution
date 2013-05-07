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



import arcgisscripting, sys, string, os, re, time, win32com.client, win32api, math
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()

def CalcDist(fromx, fromy, tox, toy):
    a = (fromy - toy)
    b = (fromx - tox)
    dist = math.hypot(a,b) 
    return dist
#Main Function
if __name__ == "__main__":
    try:
        # Input Sampe Points and Edge Netwok Feature classes
        SamplePTS = sys.argv[1] # feature Class (That has been snapped to Geonetwork) to find weighted distance between
        PointIDItem = sys.argv[2] # point FC items used to populate the top and side matrix
        OutputTableName = sys.argv[3] # Name of output table the hold weight "Matrix"
        RelTableName = "relationships" # table in GeoNetwork PGDB that hold feature relationships
        #DistanceItem = "Shape_Length" # Attribute value in GeoNetwork that weight matrix will built off of

        PGDBPath = gp.Describe(SamplePTS).Path # get the path of the Landscape network
        sampleFCName = gp.Describe(SamplePTS).Name

        ofh = open(OutputTableName, "w")
        gp.workspace = PGDBPath
        
        SourcePointList = [] # this list holds source edges to calc distance matrix
        matrixIDList = [] # this list holds sample point ids (user-defined).  It is used to create the header and side protion of the matrix.
        SourcePointXYList = [] # This list holds distance from point location to end of edge
        
        rows = gp.SearchCursor(SamplePTS) # this search cursor is to loop through all points and get attributes
        row = rows.Next()
        gp.AddMessage("  ")
        gp.AddMessage("Getting Point X,Y Coordinates ...")
        string = " ,"
        while row: # Loop through the features selected by the search query and build two lists one with IDs and the other with xy coord locations.
            FID = row.rid
            pFeat = row.shape
            xyList = pFeat.FirstPoint
            SourcePointXYList.append(xyList)
            matrixIDList.append(row.GetValue(PointIDItem)) # get rids coresponding user-defined id
            SourcePointList.append(FID)
            string = string + str(row.GetValue(PointIDItem)) + ","
            row = rows.Next()
        
        tbs = gp.ListTables(RelTableName)
        tb = tbs.next()
        if tb: # Check to see if Relationships table exists in the workspace. If it does, then run the rest of the code
            print >>ofh, string # print to file 
                   
            gp.AddMessage(" ")
            gp.AddMessage("Creating Distance Matirx --> " + str(OutputTableName))
            gp.AddMessage(" ")
            # This loop goes through each element in the SourcePointList and calculates the straight line distance from each point to everyother point
            # creating an NxN matrix
            Index1 = 0 # This index keeps track of what Point is being accessed
            for Point1 in SourcePointList:
                string = ""
                string = str(matrixIDList[Index1]) + ","
                Index2 = 0 # this keeps track of what point is being accessed
                for Point2 in SourcePointList: #This loop goes through all points and calculates a straight line distance
                    if Index1 <> Index2: # make sure that the same list is being searched
                        point1 = SourcePointXYList[Index1].split(" ")
                        point2 = SourcePointXYList[Index2].split(" ")
                        string = string + str(CalcDist(float(point1[0]), float(point1[1]), float(point2[0]), float(point2[1]))) + ","
                    else:
                        string = string + "0,"
                    Index2 = Index2 + 1 # this number keeps track of search list number
                print >>ofh, string 
                Index1 = Index1 + 1 # This keeps track of search value list
            gp.AddMessage(" ")
            gp.AddWarning("FINISHED Straight Line Distance (Symmetric) Script")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
            gp.AddMessage(" ")
        else: # Relationship table doesn't exist in geodatabase
            gp.AddMessage("Operation Terminated -> Relationship table doesn't exists in GeoDatabase")
        ofh.close() # close file
    except:
        gp.GetMessages()