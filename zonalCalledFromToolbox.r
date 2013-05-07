args = commandArgs(trailingOnly = TRUE)
args = gsub("\\\\", "/", args)
print(args)

rasterFolder = args[1]
zones = args[2]
outputFolder = args[3]
tempRDir = args[4]
runID = args[5]
zoneType = args[6]
stat = args[7]
rasterType=args[8]

##################################################################################
library(raster)
library(rgdal)
library(foreign)
startRaster = 1
endRaster = length(list.files(path=rasterFolder, pattern = paste(rasterType, "$", sep="")))

#setOptions(tmpdir=tempRDir, timer=FALSE)
rasterOptions(tmpdir=tempRDir)

###########################################
setwd(rasterFolder)
rasters=list.files(path = rasterFolder, pattern = paste(rasterType, "$", sep=""))
print(rasters)
startTime = proc.time()

zoneRaster=raster(zones)
#zoneRAT = read.dbf(paste(zones, ".vat.dbf", sep=""))
#finalData = data.frame("CATCHID"=zoneRAT$CATCHID, cellCount=zoneRAT$Count, mergeID=zoneRAT$Value)
finalData=freq(zoneRaster)
colnames(finalData)=c("CATCHID", "cellCount")
finalData=finalData[-which(is.na(finalData[,1])),]

errors=FALSE

for (r in startRaster:endRaster){
		loopStartTime=proc.time()
		valueRaster=raster(rasters[r])
		valueCropped=crop(valueRaster, zoneRaster)
		#print(valueCropped)
		zoneCropped=crop(zoneRaster, valueCropped)
		#print(zoneCropped)
		if (all(extent(valueCropped)==extent(zoneCropped), res(valueCropped)==res(zoneCropped), projection(valueCropped)==projection(zoneCropped))){
			zonalData=zonal(valueCropped, zoneCropped, stat)
			colnames(zonalData)[2]=paste(zoneType, "_", strsplit(x=rasters[r], "\\.")[[1]][1], "_", stat, sep="")
			colnames(zonalData)[1]="CATCHID"
			#tableName=paste(outputFolder, paste(strsplit(x=rasters[r], "\\.")[[1]][1], "_", runID, ".txt", sep=""), sep="\\")
			#write.csv(zonalData, tableName, row.names=FALSE, quote=FALSE, na="NA")
			finalData=merge(finalData, zonalData, by="CATCHID" , all.x = TRUE,sort=FALSE)
			tableName2=paste(outputFolder, paste("finalData_", runID, ".txt.", sep=""), sep = "\\")
			write.csv(finalData, tableName2, row.names=FALSE, quote=FALSE, na="NA")
			} else {
			if (errors==FALSE) {
				errorList=data.frame(cbind(rasters[r], extent(valueCropped)==extent(zoneCropped), (res(valueCropped)==res(zoneCropped))[1], projection(valueCropped)==projection(zoneCropped)))
				colnames(errorList)=c("raster", "extent", "resolution", "projection")
				errorList$raster=as.character(errorList$raster)
				errors=TRUE
				} else {
				errorList=rbind(errorList, c(rasters[r], extent(valueRaster)==extent(zoneRaster), (res(valueRaster)==res(zoneRaster))[1], projection(valueRaster)==projection(zoneRaster)))
				}
			}
		loopTime=as.double(((proc.time() - loopStartTime)[3] / 60))
		print (paste(sub(pattern=rasterType, replacement="", x=rasters[r]), "processed in", loopTime, "minutes"))
		}
		
if (errors==TRUE){
  errorTableName=paste(outputFolder, paste("errors", runID, ".txt", sep=""), sep="\\")
  write.csv(errorList, errorTableName, row.names=FALSE, quote=FALSE, na="NA")
  print ("Some rasters not processed due to errors")
  } else {
  print ("All rasters processed")
  }
  
minutesElapsed= as.double(((proc.time() - startTime)[3] / 60))
print(paste("Total process took", minutesElapsed, "minutes"))





