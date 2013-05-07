#Run this file to look for features incorrectly attributed as landlocked
#based on the fact that they are close to or directly touching non-landlocked features

import arcpy
from arcpy import env

env.overwriteOutput = True


############inputs 1
#tempws=r'C:\Users\menuzd\Documents\GIS_24kAttribution\temp'
#landlocked=r'C:\Users\menuzd\Documents\GIS_24kAttribution\HydroCheckFinal\Landlocked\LandlockedFlowlines.shp'
#notLandlocked=r'C:\Users\menuzd\Documents\GIS_24kAttribution\HydroCheckFinal\Landlocked\NotLandlocked.shp'
#outErrors=r'C:\Users\menuzd\Documents\GIS_24kAttribution\temp\landlockError3.shp'
#dist=0
##########################
landlocked=arcpy.GetParameter(0)
notLandlocked=arcpy.GetParameter(1)
outErrors=arcpy.GetParameter(2)
dist=arcpy.GetParameter(3)

####
arcpy.AddMessage("Selecting landlocked features that are within a distance of non-landlocked features")
arcpy.MakeFeatureLayer_management(landlocked, "landlocked.lyr", "","","")
arcpy.SelectLayerByLocation_management ("landlocked.lyr", "WITHIN_A_DISTANCE", notLandlocked, "{0} METERS".format(dist), "NEW_SELECTION")
arcpy.CopyFeatures_management ("landlocked.lyr", outErrors,"","","","")






