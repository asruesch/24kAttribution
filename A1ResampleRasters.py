#create script to resample files of interest to size we need for analysis
#do separately for categorical and continuous data....
#add buffering step to make area larger than just inBoundary...

import arcpy
from arcpy import env
import os.path

env.overwriteOutput = True


###############################################################################
rasterData = arcpy.GetParameterAsText(0) #folder with raster data that we want to resample
inBoundary=arcpy.GetParameterAsText(1) #boundary area that we want to resample- could be whole state or PUs
dem=arcpy.GetParameterAsText(2) #resamping will be done to this cell size and snapped to this feature
outputFolder=arcpy.GetParameterAsText(3) #output folder with final resampled rasters


##############################################################################
arcpy.env.workspace = rasterData

env.outputCoordinateSystem = dem
env.cellSize = dem
env.snapRaster = dem
env.extent= inBoundary

cellsize=float(str(arcpy.GetRasterProperties_management(dem, "CELLSIZEY")))

code=str(int(cellsize))

# get a list of the raster feature classes in the workspace
raster_list=arcpy.ListRasters()

# loop through the rasters
if len(raster_list)>0:
        for raster in raster_list:
                arcpy.env.overwriteOutput = True
                outfile=str(outputFolder)+"\\"+str(raster)
                #determine if raster matches cell size of zonal raster
                if float(str(arcpy.GetRasterProperties_management(raster, "CELLSIZEY")))!= cellsize:
                        #resample raster to zonal cell size if it doesn't, saving it as temp raster
                        arcpy.Resample_management(raster, outfile,cellsize, 'NEAREST')
                        arcpy.AddMessage(raster + " resampled")
                #if raster does match cell size of zonal raster
                if float(str(arcpy.GetRasterProperties_management(raster, "CELLSIZEY")))== float(cellsize):
                        arcpy.CopyRaster_management(raster, outfile)
                        arcpy.AddMessage(raster +" copied")
else:
        arcpy.AddMessage("No rasters input")
		
del raster, raster_list

