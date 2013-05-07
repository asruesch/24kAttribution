#Script to create riparian buffers
#Script prevents spurs using vertex points and is able to create riparian buffers for a large number of features
#Whereas using a simple expand does not seem to work with more than about 1000 values
#Excluding the Great Lakes coastline is hard-coded into script based on reachIDs of the great lakes seeds
#Function should probably be looped through; script crashed across the state of Wisconsin and
#was manually worked through to finish riparian buffer creation

import arcpy
import os.path
from arcpy import env
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
env.overwriteOutput = True

############################################################################
seeds=arcpy.GetParameterAsText(0) #raster of seeds
vertex=arcpy.GetParameterAsText(1) #raster of vertex points
dist=arcpy.GetParameterAsText(2) #distance that buffer will be, in same units as raster projection
outRipBuffer=arcpy.GetParameterAsText(3) #output riparian raster
##############################################################################
tempws = os.path.dirname(outRipBuffer) + "/temp"
if os.path.exists(tempws):
	arcpy.AddMessage("The tool is attempting to create a directory called temp within the directory where output watersheds will be created. A file named 'temp' already exists. Please delete or rename the folder named 'temp' or save output watersheds in a different location")
else:
	os.mkdir(tempws)
env.scratchWorkspace = tempws
env.workspace = tempws
env.cellSize = seeds
env.snapRaster = seeds
env.extent = seeds
env.outputCoordinateSystem = seeds

# Exclude Great Lakes Coasts
arcpy.AddMessage("Excluding Great Lakes")
seeds1 = SetNull(seeds, seeds, "VALUE = 600000001")
seeds2 = SetNull(seeds1, seeds1, "VALUE = 600124406")
seeds2.save('seedsFinal.img')

# Make distance raster
arcpy.AddMessage("Creating distance raster")
distance = EucDistance(seeds2, int(dist))
distance.save('distance.img')

# Cost surface for cost allocation
arcpy.AddMessage("Creating vertex cost surface")
vCost = Con(vertex, 2)
vCost.save('vCost.img')

arcpy.AddMessage("Creating second cost surface")
dCost = Con(distance >= 0, 1)
dCost.save('dCost.img')

arcpy.AddMessage("Creating final cost surface")
finalCost = Con(IsNull(vCost), dCost, vCost)
finalCost.save('finalCost.img')

# Cost Allocation
arcpy.AddMessage("Creating source raster")
source=Con(IsNull(vertex), seeds2)
source.save("source.img")

arcpy.AddMessage("Cost allocation")
alloc = CostAllocation(source, finalCost)
alloc.save("allocation.img")

#Get rid of seed area
arcpy.AddMessage("Extracting final buffer")
ripBuff=Con(IsNull(seeds2), alloc)
ripBuff.save(outRipBuffer)

