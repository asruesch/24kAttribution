#script to run trace to watershed of designated size
#currently runs trace whether or not there is a dam between feature and great lake, with idea that dam 
#presence/ absence could be an additional output
#also, currently does not aggregate duplicate features such as lakes
#what to do with features with no watershed but in edges? some may have sheds >=x km, others may not
#probably can just not attribute, but use in trace...

#trial values
# ###########################################################################################
# edgesTable="C:\\Users\\menuzd\\Documents\\GIS_24kAttribution\\temp\\allDataEdges2.csv"
# traceid="TRACEID" 
# reachField="REACHID" 
# lengthField="Shape_Leng" 
# damField="DAMSIDE" 
# watershedArea="shedArea" 
# shedThreshold=as.numeric(10)
# relationshipTable="C:\\Users\\menuzd\\Documents\\GIS_24kAttribution\\temp\\allDataRels.csv" 
# fromid="FROM_TRACEID"  
# toid="TO_TRACEID"
# outputTable="C:\\Users\\menuzd\\Documents\\GIS_24kAttribution\\temp\\allDataDownstreamOutput.csv"

############################################################################################
args = commandArgs(trailingOnly = TRUE)
args = gsub("\\\\", "/", args)

edgesTable=args[1]
traceid=args[2]
reachField=args[3]
lengthField=args[4]
damField=args[5]
watershedArea=args[6]
shedThreshold=as.numeric(args[7])
relationshipTable=args[8]
fromid=args[9]
toid=args[10]
outputTable=args[11]

############################################################################################
edges2=read.csv(edgesTable)
rels=read.csv(relationshipTable)

edges2$isBigShed=ifelse(edges2[[watershedArea]]>=shedThreshold,  1, 0)
edges2$isBigShed=ifelse(is.na(edges2$isBigShed), 0, edges2$isBigShed)

#combine relationship table with edge data on from side
fromMerge=merge(rels, edges2, by.x=fromid, by.y=traceid)
#select all columns that we are interested in
fromMerge2=data.frame(fromMerge[[fromid]], fromMerge[[toid]], fromMerge[[reachField]], 
fromMerge[[lengthField]], fromMerge[[damField]], fromMerge$isBigShed)
colnames(fromMerge2)=c("fromfeat", "tofeat", "FROMID", "FROMLENGTH", "FROMDAM", "FROMSHED")
cols=dim(fromMerge2)[2]#this just helps in case we change the number of fields that we use
#the select columns below should not need to be changed as long as both "to" and "from" info is populated
#however, will have to adjust colFiller below if additional fields are added

#combine relationship table with edge data on "to" side
toMerge=merge(fromMerge2, edges2, by.x="tofeat", by.y=traceid)
mergedData=data.frame(toMerge[,1:cols], toMerge[[reachField]], 
toMerge[[lengthField]], toMerge[[damField]],toMerge$isBigShed)
colnames(mergedData)=c(colnames(mergedData)[1:cols], "TOID", "TOLENGTH", "TODAM", "TOSHED")

#processing of lsn- add in info about "to" features into from column for features not found in "to" column", with NA populating the missing "to" columns
missingFroms=which(is.element(mergedData$tofeat, mergedData$fromfeat)==FALSE)
newData= mergedData[missingFroms,c(1,(cols+1):(cols*2-2))]
colFiller=rep(NA, length(missingFroms))
newDataFilled=data.frame(colFiller,newData, colFiller, colFiller, colFiller, colFiller)
colnames(newDataFilled)=colnames(mergedData)
newDataFilledFinal=aggregate(newDataFilled, by=list(newDataFilled$fromfeat), FUN=mean)[,2:(cols+cols-1)]

#final data frame
lsndata=rbind(mergedData, newDataFilledFinal)

###############################################################################################################
######################  function for traces  ###########################
getRowNum=function(fromfeat){
	return(which(lsndata$fromfeat==fromfeat))
	}
###############################################################################################################
tracedata=subset(lsndata, lsndata$FROMSHED!=1) #otherwise feature is already a big shed
fromfeat=array(0, dim(tracedata)[1])
reachID=array(0, dim(tracedata)[1])
distance=array(NA, dim(tracedata)[1])
dam=array(0, dim(tracedata)[1])
x=0

i = 0
pb = txtProgressBar(min=0, max=dim(tracedata)[1], style=3)
stTime <- Sys.time()

for (f in tracedata$fromfeat){
	i = i + 1
	setTxtProgressBar(pb, i)
	x=x+1
	flagDown=FALSE
	l=0
	fromfeat[x]=f
	rowNum=getRowNum(f)
	reachID[x]=lsndata$FROMID[rowNum]
	#we only have features that ARE NOT big sheds, so we don't need if/else statement here
	l=l+lsndata$FROMLENGTH[rowNum]/2
	new=lsndata$tofeat[rowNum]
	newRow=getRowNum(new)
	if (lsndata$FROMDAM[rowNum]==2){
		dam[x]=1
	}
	while (flagDown==FALSE) {
		if (is.na(new)){
			flagDown=TRUE
		} else if (lsndata$FROMSHED[newRow]==1){ #if  feature we traced to is a big shed
			if (lsndata$FROMDAM[newRow]==1){ #if dam is on upstream side, then add dam in attributes
				dam[x]=1
			}
			distance[x]=l	
			flagDown=TRUE
		} else if (lsndata$FROMDAM[newRow]>0){
			dam[x]=1
		}
		l=l+lsndata$FROMLENGTH[newRow]
		new=lsndata$tofeat[newRow]
		newRow=getRowNum(new)
	}	
}
output=data.frame(fromfeat, reachID,distance, dam)
bigShedData=subset(lsndata, lsndata$FROMSHED==1) #subset out data that is big shed
bigShedData2=data.frame(bigShedData$fromfeat, bigShedData$FROMID,
rep(0, nrow(bigShedData)), rep(0, nrow(bigShedData)))
colnames(bigShedData2)=c("fromfeat", "reachID", "distance", "dam")
mergedOutput=rbind(output, bigShedData2)
close(pb)
endTime <- Sys.time()
procDur <- difftime(endTime, stTime, units="mins")
print(paste("Trace took", signif(as.numeric(procDur), digits=2), "minutes to run"))

write.csv(mergedOutput, outputTable, row.names=FALSE)


###############################################################################################################
output=mergedOutput[which(!mergedOutput$fromfeat %in% bigShedData2$fromfeat),]






y=which(output$distance<10)















