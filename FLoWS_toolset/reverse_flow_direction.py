# reverse the line direction of an input edge feature class to create a new edge feature class
import arcgisscripting, sys, string, os, re, time #win32com.client
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()


try:
    #get the input edge featureclass name
    InEdgeFeatureclass = sys.argv[1]
    # get the name and location of the new reversed direction edge featureclass
    OutputEdgeFeatureclass = sys.argv[2]
    InEdgeFeatureclass = gp.Describe(InEdgeFeatureclass).Path + "\\" + gp.Describe(InEdgeFeatureclass).Name
    
    #create new output featureclass
    gp.CreateFeatureclass(os.path.dirname(OutputEdgeFeatureclass), os.path.basename(OutputEdgeFeatureclass), "Polyline", InEdgeFeatureclass)
    #gp.defineprojection(OutputEdgeFeatureclass, projection)
    # Open an Insertcursor for the new feature class
    edgeCur = gp.InsertCursor(OutputEdgeFeatureclass)
    # create the array and point objects neede to create a feature
    lineArray = gp.CreateObject("Array")
    linePNT = gp.CreateObject("Point")
    # Open an searchcursor that goes through all edge in InEdgeFeatureclass
    Edgerows = gp.SearchCursor(InEdgeFeatureclass)
    Edgerow = Edgerows.Next()

    #Check that new featureclass has the same field names.  This is done because ESRI modifies field names is some cases     
    ExistingFieldsList = []
    MissingFieldsList = []
    edgeFields = gp.listfields(InEdgeFeatureclass)
    edgeField = edgeFields.Next()
    while edgeField:
        if gp.ListFields(OutputEdgeFeatureclass, edgeField.Name).Next():
            ExistingFieldsList.append(edgeField.Name)
        else:
            MissingFieldsList.append(edgeField.name)
        edgeField = edgeFields.Next()
        
    gp.AddMessage("  ")
    gp.AddMessage("  ")
    gp.AddMessage("Reversing Edges....")
    gp.AddMessage("  ")
    gp.AddMessage("  ")
    while Edgerow:
        edgeFeature = Edgerow.shape # get the geo of the selected feature
        a = 0
        while a < edgeFeature.PartCount:
            edgeArray = edgeFeature.GetPart(a) # get a line with in the featureclass and load it x,y coords into a array
            edgeArray.Reset
            pnt = edgeArray.Next()
            EdgeList = []
            while pnt:
                EdgeList.append(str(pnt.x) + "," + str(pnt.y))
                pnt = edgeArray.Next()
            EdgeList.reverse()
            count = 0
            newFeature = edgeCur.NewRow() # create a new row to insert the feature into
            for point in EdgeList:
                pointList = point.split(",")
                linePNT.id = count
                linePNT.x = float(pointList[0])
                linePNT.y = float(pointList[1])
                lineArray.add(linePNT)
                count = count + 1
            edgeFields = gp.listfields(InEdgeFeatureclass)
            edgeField = edgeFields.Next()
            #Populate attribute fields...
            skip = 0
            for name in ExistingFieldsList:
                if skip > 1:
                    newFeature.setvalue(name, Edgerow.GetValue(name))
                skip = skip + 1
            newFeature.shape = lineArray # set the geometery of the new feature to the array of points
            edgeCur.InsertRow(newFeature)
            lineArray.RemoveAll()
            a = a + 1
        Edgerow = Edgerows.Next()
    gp.AddMessage("  ")
    gp.AddMessage("  ")
    if len(MissingFieldsList) > 0:
        gp.AddWarning("The flowing fields for feature class " + InEdgeFeatureclass + " have not been calculated because their names")
        gp.AddWarning("have been modified by ESRI.  This can be resolved by joining on FID and using the field calculator")
        gp.AddError("Modified field names:")
        for fieldname in MissingFieldsList:
            gp.AddError("  " + str(fieldname))
        gp.AddMessage("  ")
        gp.AddMessage("  ")
    gp.AddWarning("Finished Reverse Flow Direction Script")
    gp.AddMessage("  ")
    gp.AddMessage("  ")
except:
        print gp.GetMessages(2)