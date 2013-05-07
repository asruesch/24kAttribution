# create-hca.py
# Create HCAs using DEM, Flow Direction, Reach, and water Body grids
# Import system modules

import arcgisscripting, sys, string, os, re, time #win32com.client
from time import *

# Create the Geoprocessor object
# gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
gp = arcgisscripting.create()

try:
    # Get User Inputs
    InDEM = sys.argv[1]             # DEM Raster Layer         
    InFlowDir = sys.argv[2]         # Flow Direction Raster Layer 
    InReach = sys.argv[3]           # Reach Raster Layer
    InWaterBody = sys.argv[4]       # Water Body Raster Layer
    OutHCAshapefile = sys.argv[5]   # Output shapefile name and location
    WKSpace = sys.argv[6]           # temp. workspace 

    # Get full path and Name for inputs
    InDEM = gp.Describe(InDEM).Path + "\\" + gp.Describe(InDEM).Name
    InFlowDir = gp.Describe(InFlowDir).Path + "\\" + gp.Describe(InFlowDir).Name
    InReach = gp.Describe(InReach).Path + "\\" + gp.Describe(InReach).Name
    if InWaterBody <> "#": 
        InWaterBody = gp.Describe(InWaterBody).Path + "\\" + gp.Describe(InWaterBody).Name
    # Check out Spatial Analyst extension license
    gp.CheckOutExtension("Spatial")
    gp.Workspace = WKSpace
        
    strWS = "RCA" + strftime("%Y%m%d%H%M%S", localtime())
    gp.CreateFolder ( gp.Workspace, strWS )
    gp.Workspace = gp.Workspace + "/" + strWS
    gp.AddMessage(" ")
    gp.AddMessage("Writing RCA tempuary files to workspace: " + gp.Workspace )

    # set output extent of create HCA to the area displayed on the screen
    #gp.Extent = InDEM
    gp.overwriteoutput = 1
    
       
    # Perform zonalstats on water bodies and reaches to get the maximum reach OID value
    # within a waterbody.
    if InWaterBody <> "#":
        gp.AddMessage(" ")
        gp.AddMessage("Finding reach OIDs that match waterbodies....")
        gp.AddMessage("  ")
        if gp.Exists("burntemp"):
            gp.Delete("burntemp")
        gp.ZonalStatistics_sa(InWaterBody, "Value", InReach, "burntemp", "maximum", "DATA")
        InRaster = "burntemp"
    else:
        InRaster = InReach
        
    # Merge Burntemp and buffered reaches grids into seed10
    if gp.Exists("seed10"):
        gp.Delete("seed10")
    if InWaterBody <> "#":
        gp.AddMessage(" ")
        gp.AddMessage("Merging reach raster with new waterbodies to create seed raster")
        gp.AddMessage("  ")
        string = InReach + ";" + gp.Workspace + "\\" + "burntemp"
        gp.AddMessage(string)
        gp.MosaicToNewRaster(string, gp.Workspace, "seed10")
    else:
        gp.CopyRaster(InReach, gp.Workspace + "\\seed10")

    # Get the spatial extent of the c:/temp/seed10 raster for input into create contant raster

    desc = gp.Describe(InDEM)

    #gp.Extent = InDEM
    gp.Extent = "MAXOF"
    rasterExtent = desc.extent
    cellSize = desc.MeanCellHeight
    #gp.AddMessage(str(cellSize))
    # Create constant value grids
    constantValue = 0
    
    # Create constant grid "trueras" with a value of 0
    gp.AddMessage("Creating Contstant grids....")
    gp.AddMessage("   ")
    #gp.AddMessage("    Creating trueras")
    #gp.AddMessage("   ")
    if gp.Exists("trueras"):
        gp.Delete("trueras")
    gp.CreateConstantRaster_sa("trueras", constantValue, "INTEGER", cellSize, rasterExtent)

    constantValue = 10
    # create constant grid "conten" with a value of 10
    #gp.AddMessage("    Creating Conten")
    #gp.AddMessage("   ")
    if gp.Exists("conten"):
        gp.Delete("conten")
    gp.CreateConstantRaster_sa("conten", constantValue, "INTEGER", cellSize, rasterExtent)

    constantValue = 1
    # create constant grid "trueras1" with a value of 1
    #gp.AddMessage("    Creating trueras1")
    #gp.AddMessage("   ")
    if gp.Exists("trueras1"):
        gp.Delete("trueras1")
    gp.CreateConstantRaster_sa("trueras1", constantValue, "INTEGER", cellSize, rasterExtent)

    #   ------------------------------------------------------
    #   ---     this is where the while loop will begin     ----
    #   ------------------------------------------------------
    x = 1
    iterations = 5
    gp.AddMessage("Creatinig RCA Rasters....")
    gp.AddMessage("   ")    
    while x < iterations:
        gp.AddMessage("Iteration " + str(x) + " Out Of " + str(iterations) + " Total Iterations")
        gp.AddMessage("   ")
        # populate list with rasters names to delete
        # RasterList = []
        # RasterList = ['watershed','holes','holesnull','holesreg','holemin','holeminten','zonesmart','zonesmart1','smartgrow','smgrow','watershed2']
       
        # Calculate Watershed uing seed10 and flow direction
        gp.AddMessage("     Calculating watersheds using seed raster")
        gp.AddMessage("   ")
        if gp.Exists("watershed"):
            gp.Delete("watershed")
        gp.Watershed_sa(InFlowDir, "seed10", "watershed")

        # Find Null values in watershed grid and create holes
        gp.AddMessage("     Creating Holes grid")
        gp.AddMessage("   ")
        if gp.Exists("holes"):
            gp.Delete("holes")
        gp.IsNull_sa("watershed", "holes")
        
        # Run a conditional statement that evaluates if a watershed has no data if it does, then
        # it is assigned a value of zero from the trueras grid
        gp.AddMessage("     Creating holesnull grid -> Running constatment")
        gp.AddMessage("   ")
        if gp.Exists("holesnull"):
            gp.Delete("holesnull")
        gp.Con_sa("holes", "trueras", "holesnull")

        # Region Group is used to assign unique values to all hole regions
        gp.AddMessage("     Running Region Group on the holesnull grid")
        holesnull = gp.Workspace + "\\holesnull"
        holesreg = gp.Workspace + "\\holesreg"
        gp.AddMessage("   ")
        if gp.Exists("holesreg"):
            gp.Delete("holesreg")
        #gp.AddMessage("Workspace is set to--> " + gp.Workspace)
        #gp.RegionGroup_sa("holesnull", "holesreg", "FOUR", "WITHIN", "NO_LINK")
        gp.RegionGroup("holesnull", "holesreg",  "FOUR", "WITHIN", "NO_LINK")

        #gp.AddMessage(gp.Describe("holesreg").Path)        
        # Run zonal Stats on holesreg to find the min. elevation with in each hole region
        gp.AddMessage("Workspace is set to--> " + gp.Workspace)
        gp.AddMessage("     Getting the Min. elevation within each hole region")
        gp.AddMessage("   ")
        if gp.Exists("holemin"):
            gp.Delete("holemin")
        gp.ZonalStatistics_sa("holesreg", "Value", InDEM, "holemin", "minimum", "DATA")

        # Add conten raster to holemin raster to create holeminten raster
        gp.AddMessage("     Adding holemin with conten to create holeminten ")
        gp.AddMessage("   ")
        if gp.Exists("holeminten"):
            gp.Delete("holeminten")
        gp.Plus_sa("holemin", "conten", "holeminten")

        # Find all areas of elevation that are less than the minimum elevation + 10 for each hole region and assigning them a value of one
        gp.AddMessage("     Finding areas of elevation that are less than the minimum elevation + 10")
        gp.AddMessage("   ")
        if gp.Exists("zonesmart"):
            gp.Delete("zonesmart")
        gp.LessThan_sa(InDEM, "holeminten", "zonesmart")

        # Conditional statment using zonesmart as the true/false raster and trueras1 as the true value grid
        gp.AddMessage("     Running con statment with zonesmart and trueras1 to create zonesmart1")
        gp.AddMessage("   ")
        if gp.Exists("zonesmart1"):
            gp.Delete("zonesmart1")
        gp.Con_sa("zonesmart", "trueras1", "zonesmart1")

        # Merge watershed and zonesmart rasters to create smartgrow raster
        gp.AddMessage("     Merging watershed and zonesmart rasters to create smartgrow raster")
        gp.AddMessage("   ")
        if gp.Exists("smartgrow"):
            gp.Delete("smartgrow")
        #gp.MosaicToNewRaster("watershed;zonesmart1", gp.Workspace, "smartgrow")
        gp.MultiOutputMapAlgebra("smartgrow = merge(watershed, zonesmart1)")
        # Replaces cells of a raster corresponding to a mask, with the values of the nearest neighbors
        gp.AddMessage("     Nibbling smartgrow with watershed")
        gp.AddMessage("   ")
        if gp.Exists("smgrow1"):
            gp.Delete("smgrow1")
        gp.Nibble_sa("smartgrow", "watershed", "smgrow1")

        # Calculate Wateshed boundries with new seed raster, smgrow1, to create new seed raseter for next iteration
        gp.AddMessage("     Calculating watershed boundries using smgrow1 as seed")
        gp.AddMessage("   ")
        
        x = x + 1
        if x < iterations:
            if gp.Exists("seed10"):
                gp.Delete("seed10")        
            gp.Watershed_sa(InFlowDir, "smgrow1", "seed10")
            
    gp.AddMessage("Creating Landscape Feature Classes....")
    gp.AddMessage("  ")
    if gp.Exists("watershed2"):
        gp.Delete("watershed2")
    gp.Watershed_sa(InFlowDir, "smgrow1", "watershed2")
    
    if gp.Exists("watergrp"):
        gp.Delete("watergrp")
    gp.RegionGroup_sa("watershed2", "watergrp", "FOUR", "WITHIN")
    
    if gp.Exists("waternull"):
        gp.Delete("waternull")
    gp.SetNull_sa("watergrp", "watershed2", "waternull", "count < 2")
    
    if gp.Exists("watershed3"):
        gp.Delete("watershed3")
    gp.Nibble_sa("watershed2", "waternull", "watershed3")
    
    # gp.BoundaryClean("C:/temp/watershed2", "C:/temp/watershed3", "DESCEND", "ONE_WAY")        

    gp.RasterToPolygon_conversion("watershed3", "temp_rca.shp", "SIMPLIFY", "Value")
    gp.AddMessage(" ")
    gp.AddMessage("Dissolveing Multi-part Polygons")
    gp.Dissolve_management("temp_rca.shp", OutHCAshapefile + ".shp", "GRIDCODE", "#", "MULTI_PART")

    # Process: Add Field...
    gp.AddField_management(OutHCAshapefile + ".shp", "rca_id", "LONG", "16", "", "", "", "NON_NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field...
    gp.AddMessage(" ")
    gp.AddMessage("Calculating RCA ID field rca_id for RCA shapefile " + OutHCAshapefile + " ...")
    gp.AddMessage(" ")
    gp.CalculateField_management(OutHCAshapefile + ".shp", "rca_id", "[GRIDCODE]")
    
    gp.AddWarning("Finished Create RCAs Script")
    gp.AddMessage(" ")
    gp.AddMessage(" ")


except:
    # Print error message if an error occurs
    gp.GetMessages()    
    