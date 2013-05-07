#instructions for using with current database
#1) join reaches with baseAttributes based on REACHID
#1) export to table, or if this crashes, export to shapefile and then export new shapefile to table
#2) potentially edit this table, you need the columns indicated below, which will be SHAPE_LENGTH, etc.
#3) create stopTraceField by selecting all features where seedType=Great Lakes or (something in Baseattributes)
#and make those features have a value of 1, give remaining features value of 0

#need to check that great lakes exclusions work correctly
#there could a lake with a dam and part of lake is able to get to target lake, but the rest can't
#max search dist includes distance of last feature searched, so can exceed distance set by script
#if you want every traceID to output an individual attribute, just use TrACEID for reachid
#features that are completely isolated (no to or from relationships) will not be attributed; these should 
#just be lakes and/or there might not be any at all but search for anything with a null value and attribute manually

args = commandArgs(trailingOnly = TRUE)
args = gsub("\\\\", "/", args)

maxDist=as.numeric(args[1])
lakeMin=as.numeric(args[2])
lakeMax=as.numeric(args[3])
relationshipTable=args[4]
fromID=args[5]
toID=args[6]
flowlineData=args[7]
IDcol=args[8]
reachField=args[9]
lengthField=args[10]
damField=args[11]
stopTraceField=args[12]
lakeAreaField=args[13]
outputTable=args[14]

############################################################################################
#library allows access to mdb tables
rels=read.csv(relationshipTable, header=TRUE)
edges=read.csv(flowlineData, header=TRUE)

edges2=edges
edges2$isLake=ifelse(edges2[[lakeAreaField]]>=lakeMin & edges2[[lakeAreaField]]<lakeMax, 1, 0)
edges2$isLake=ifelse(is.na(edges2$isLake), 0, edges2$isLake)

#combine relationship table with edge data on from side
fromMerge=merge(rels, edges2, by.x=fromID, by.y=IDcol)
#select all columns that we are interested in
fromMerge2=cbind(fromMerge[[fromID]], fromMerge[[toID]], fromMerge[[reachField]], fromMerge[[lengthField]], fromMerge[[damField]],
fromMerge$isLake,fromMerge[[stopTraceField]])

colnames(fromMerge2)=c("fromfeat", "tofeat", "FROMID", "FROMLENGTH", "FROMDAM","FROMLAKE", "FROMGL")
cols=dim(fromMerge2)[2] #this just helps in case we change the number of fields that we use
#the select columns below should not need to be changed as long as both "to" and "from" info is populated
#however, will have to adjust colFiller below if additional fields are added

#combine relationship table with edge data on "to" side
toMerge=merge(fromMerge2, edges2, by.x="tofeat", by.y=IDcol)
mergedData=cbind(toMerge[,1:cols], toMerge[[reachField]], toMerge[[lengthField]], toMerge[[damField]],
toMerge$isLake, toMerge[[stopTraceField]])
colnames(mergedData)=c(colnames(mergedData)[1:cols], "TOID", "TOLENGTH", "TODAM", "TOLAKE", "TOGL")

#processing of lsn- add in info about "to" features into from column for features not found in "to" column", with NA populating the missing "to" columns
missingFroms=which(is.element(mergedData$tofeat, mergedData$fromfeat)==FALSE)
newData= mergedData[missingFroms,c(1,(cols+1):(cols*2-2))]
colFiller=rep(NA, length(missingFroms))
newDataFilled=cbind(colFiller, newData, colFiller, colFiller, colFiller, colFiller, colFiller)
colnames(newDataFilled)=colnames(mergedData)
newDataFilledFinal=aggregate(newDataFilled, by=list(newDataFilled$fromfeat), FUN=mean)[,2:(cols+cols-1)]

#final data frame
lsndata=rbind(mergedData, newDataFilledFinal)
###############################################################################################################
######################  functions for traces  ###########################
#downstream functions
firstLength=function(){ #returns half the length of the feature
	l=(lsndata$FROMLENGTH[downDataTemp[1]])/2
	return(l)
	}
Length=function(){  #return length of feature plus cumulative lenght to get to feature
	l=lsndata$FROMLENGTH[downDataTemp[1]]+downDataTemp[2] #length is new length plus cumulative length
	return(l)
	}
getAllUps=function(first){ #first is true or false for whether feature is first segment to process
	if (first==TRUE){
		l=firstLength()
		oldFeature=FALSE  #don't have any "old" features, so just set as dummy variable for now
	} else if (first==FALSE){
		l=rep(downDataTemp[2])  #cumulative length to get to feature, distance of feature not included
		}
	tos=which(lsndata$tofeat==lsndata$fromfeat[downDataTemp[1]]) #find all tos connected to a point upstream
	lgnth=rep(l, length(tos))
	isLake=lsndata$FROMLAKE[tos]
	newUps=cbind(tos, lgnth, isLake)
	allUps=rbind(allUps, newUps[which(newUps[,1]!=oldFeature),])
	return(allUps)
}			
getNextDown=function(first){
	if (first==TRUE){
		l=firstLength()
	} else if (first==FALSE){
		l=Length()
		}
	nextTo=which(lsndata$fromfeat==lsndata$tofeat[downDataTemp[1]]) 
	downData=c(nextTo,l,lsndata$FROMLAKE[nextTo])
	return(downData)
	}


############## running trace to nearest lake in any direction taking into account dams
i = 0
pb = txtProgressBar(min=0, max=dim(lsndata)[1], style=3)
stTime <- Sys.time()
finalData=data.frame(lsndata$FROMID, rep(NA, length(lsndata$FROMID)),rep(NA, length(lsndata$FROMID)), rep(NA, length(lsndata$FROMID)))

for (rownum in 1:dim(lsndata)[1]){
	i = i + 1
	setTxtProgressBar(pb, i)

tos=rownum
downData=c(tos, 0, lsndata$FROMLAKE[tos])
downDataTemp=downData
flagDown=FALSE  #downstream trace ends when this is true
flagUp=FALSE  #upstream trace ends when this is true
nearestLake=c(NA, maxDist) #placeholder to hold onto nearest lake info and lake ID
maxSearchDist=0

allUps=matrix(nrow=0, ncol=3) 

#run first feature separately because length and dam treatment is somewhat different
#assuming we don't want attribute great lakes features, we will leave as NA for now, will be converted to -999 in final output
if (lsndata$FROMGL[tos]==1){
	flagDown=TRUE
} else if (downData[3]==1){  #if this site is a lake, then don't do while loop and set dist to 0 with feature's own ID, allUps will be zero already
	flagDown=TRUE
	finalData[tos,2:3]=c(lsndata$FROMID[tos], 0)
} else if (lsndata$FROMDAM[downData[1]]==2){ #if feature has dam on downstream side & isn't a lake, find upstream connection and end downstream trace
	allUps=getAllUps(TRUE) 
	flagDown=TRUE
} else if (lsndata$FROMDAM[downData[1]]==1){ #if feature has dam on upstream side, move down one without going upstream
	oldFeature=downData[1]
	downData=getNextDown(TRUE)
} else {  #feature not a lake and with no dams
	allUps=getAllUps(TRUE)
	
	oldFeature=downData[1]
	downData=getNextDown(TRUE)
	}
	
if (length(downData)<2){  #if there is no feature to trace downstream to, end downstream process, may still trace upstream
		flagDown=TRUE
} else {
	downDataTemp=downData
	}
	
#downstream trace and accumulating file of all upstream segments to analyze later
while (flagDown==FALSE) {
	maxSearchDist=downDataTemp[2]
	if (downDataTemp[3]==1 & lsndata$FROMDAM[downDataTemp[1]]!=1 & downDataTemp[2]<nearestLake[2]){  #if feature is a lake and doesn't have an upstream dam and is closer than max search dist
		nearestLake=c(lsndata$FROMID[downDataTemp[1]], downDataTemp[2]) #then assign nearest lake as that REACHID and that length
		flagDown=TRUE  #don't need to trace down PAST this feature if this feature is a lake
	} else if (downDataTemp[2]<nearestLake[2]){ #if segment is not downstream lake but is closer than the max distance we set
		allUps=getAllUps(FALSE)
	} else {  #end process if the feature we are tracking is further down the river than the max distance we are using
		flagDown=TRUE
	}
#ends downstream trace if we have reached a dam or a Great Lakes hydroline, accumulating attached Ups first
#we have accounted for dammed features that are lakes with dam on downstream side above
	if (lsndata$FROMDAM[downDataTemp[1]]>0 | lsndata$FROMGL[downDataTemp[1]]==1){ 
		flagDown=TRUE
	}
	oldFeature=downData[1]
	downData=getNextDown(FALSE)
	if (length(downData)<2){  #basically, if there aren't any more features in downData (though l(ength) may still exist)
		flagDown=TRUE
		}
	downDataTemp=downData
	}

#upstream trace using segments identified earlier	
#first, remove any features that may be Great Lakes lines, don't want to trace on these
#this would only happen if feature flows TO a great lakes line and also has a great lakes line merging into it
if (length(allUps)==0){ #end process if we don't have any accumulated upstream data
	flagUp=TRUE
} else {
	allUpsNew=matrix(allUps[which(lsndata$FROMGL[allUps[,1]]!=1),], ncol=3)
	upDataTemp=allUpsNew
  if (length(allUpsNew)==0){ #end process if we don't have any accumulated upstream data
	flagUp=TRUE
	}
}

while (flagUp==FALSE) {
	upData=matrix(nrow=0, ncol=3)  #creates empty matrix to put data in 
	for (seg in 1:dim(upDataTemp)[1]){  #loop through total number of rows in file, through each stream segment	
		if (upDataTemp[seg,3]==1 & upDataTemp[seg,2]<nearestLake[2] & lsndata$FROMDAM[upDataTemp[seg,1]]!=2){ #if this segment is a lake that is closer than other nearest lakes and is not dammed on downstream side
			nearestLake=c(lsndata$FROMID[upDataTemp[seg,1]], upDataTemp[seg,2])
		} else if (lsndata$FROMDAM[upDataTemp[seg,1]]==0){ #if segment isn't dammed, regardless of where dam is, get upstream connections
			tos=which(lsndata$tofeat==lsndata$fromfeat[upDataTemp[seg,1]]) #find all tos connected to a point
			lgnth=rep(lsndata$FROMLENGTH[upDataTemp[seg,1]]+upDataTemp[seg,2], length(tos)) #creates a cumulative length traveled so far to get to feature by adding previous length to 
			isLake=lsndata$FROMLAKE[tos] #whether feature that we got to now is a lake or not
			upData=rbind(upData, cbind(tos, lgnth, isLake)) #bind new upstream features into matrix
		}
		if (length(tos)>0){  #if there are upstream features for this segment, update maximum search distance
			maxSearchDist=max(maxSearchDist, upDataTemp[seg,2])
		} else { #otherwise, once we've reached the end of a trace, add in the last features length to the total length traveled
			newDist=upDataTemp[seg,2]+lsndata$FROMLENGTH[upDataTemp[seg,1]]
			maxSearchDist=max(maxSearchDist, newDist)
			}
	}
	#this is potentially only place to remove the which and replace with subset, but not making change just in case
	upDataTemp=matrix(upData[which(upData[,2]<nearestLake[2]),], ncol=3)  #keep only those features that are less than the cutoff for nearest lake
	if (length(upDataTemp)==0){
		flagUp=TRUE
		}
	}
if (is.na(nearestLake[1])==FALSE){
	finalData[rownum, 2:3]=nearestLake
	}
finalData[rownum, 4]=maxSearchDist

}

colnames(finalData)=c("REACHID", "NearLake", "NearLakeDist", "maxSearchDist")
close(pb)
endTime <- Sys.time()
procDur <- difftime(endTime, stTime, units="mins")
print(paste("Trace took", signif(as.numeric(procDur), digits=2), "minutes to run"))

noNAdat=finalData[which(is.na(finalData$NearLakeDist)==FALSE),]
noNAagg=aggregate(noNAdat, by=list(noNAdat$REACHID), FUN=mean)[,2:5]
NAdat=finalData[which(is.na(finalData$NearLakeDist)==TRUE),]
NAagg=aggregate(NAdat, by=list(NAdat$REACHID), FUN=mean)[,2:5]
diffs=setdiff(NAagg$REACHID, noNAagg$REACHID)
NAagg2=NAagg[which(NAagg$REACHID %in% diffs),]
output=rbind(noNAagg, NAagg2)

write.csv(output, outputTable, row.names=FALSE)


# x=merge(edges, output, by.x="REACHID", by.y="REACHID")
# x2=x[is.na(x$medLake)==FALSE,]
# diff=x2$LAKE_SM_DI-round(x2$medDist, 0)
# x3=x2[which(diff!=0),]