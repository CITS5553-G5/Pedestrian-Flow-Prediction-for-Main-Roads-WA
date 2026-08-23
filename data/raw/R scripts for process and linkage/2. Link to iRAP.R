# Link to iRAP
require(data.table)
 
# user
system  = Sys.info()
if(system["user"] == "00058985"){
  bdir    = "C:/Users/00058985/OneDrive - UWA/WACRSR/Ped iRAP/"
} else {
  bdir    = "C:/Users//....."
}
saveloc = paste0(bdir, "Data/")

dfirap = fread(file = paste0(saveloc, "AusRAP Data - Codes.csv"))

#dfirap = fread(file = paste0(saveloc, "AusRAP Data - Words.csv"))
dfped   = fst::read.fst(path = paste0(saveloc, "Ped_Data.fst"), as.data.table = T)
dfbike  = fst::read.fst(path = paste0(saveloc, "Bike_Data.fst"), as.data.table = T)

setkey(dfped, ID, Session)
setkey(dfbike, ID, Session)
dfpb    = merge(dfped, dfbike[, .(ID, Session, bike_obs_peak_along, bike_24_total_ave)])
dfpb    = dfpb[Day == "THURSDAY"]
dfpb[, StartSLK := SLK - 0.1]
dfpb[, EndSLK   := SLK + 0.1]

# reduce data table to mostly only necessary for now
dfirap = dfirap[, .(`Road No`, `Start SLK`, `End SLK`,
                    #`Pedestrian observed flow across the road`, `....along the road driver-side`, `...along the road passenger side`, # Not useful all none
                    `Pedestrian peak hour flow across the road`,
                    `Pedestrian peak hour flow along the road driver-side`,
                    `Pedestrian peak hour flow along the road passenger-side`,
                    `Bicycle peak hourly flow`
                    )]

setnames(dfirap, names(dfirap),
    c("ROAD_NO", "StartSLK", "EndSLK", "Ped_Peak_Cross", "Ped_Peak_Driver", "Ped_Peak_Passenger", "Bike_Peak_Flow"))

# Recode counts to sensible
RECOUNT = c("1" = 0,
            "2" = 3,
            "3" = 15,
            "4" = 38,
            "5" = 75,
            "6" = 150,
            "7" = 250,
            "8" = 350,
            "9" = 450)

dfirap[, Ped_Peak_Cross          := RECOUNT[as.character(Ped_Peak_Cross)]]
dfirap[, Ped_Peak_Driver         := RECOUNT[as.character(Ped_Peak_Driver)]]
dfirap[, Ped_Peak_Passenger      := RECOUNT[as.character(Ped_Peak_Passenger)]]
dfirap[, Bike_Peak_Flow          := RECOUNT[as.character(Bike_Peak_Flow)]]

# Process sums
dfirap[, Ped_Peak_Along          := Ped_Peak_Driver + Ped_Peak_Passenger]
dfirap[, Ped_Peak_Total          := Ped_Peak_Cross + Ped_Peak_Driver + Ped_Peak_Passenger]

dfirap[EndSLK < StartSLK, c("EndSLK", "StartSLK") := .(StartSLK, EndSLK)]

# Merge irap and ped
setkey(dfpb, ROAD_NO, StartSLK, EndSLK)
setkey(dfirap, ROAD_NO, StartSLK, EndSLK)

dfm = foverlaps(dfpb, dfirap)
dfm = dfm[, .(Ped_Peak_Cross         = mean(Ped_Peak_Cross),
              Ped_Peak_Driver        = mean(Ped_Peak_Driver),
              Ped_Peak_Passenger     = mean(Ped_Peak_Passenger),
              Ped_Peak_Along         = mean(Ped_Peak_Along),
              Ped_Peak_Total         = mean(Ped_Peak_Total),
              Bike_Peak_Flow         = mean(Bike_Peak_Flow),
              max_Ped_Peak_Cross     = max(Ped_Peak_Cross),
              max_Ped_Peak_Driver    = max(Ped_Peak_Driver),
              max_Ped_Peak_Passenger = max(Ped_Peak_Passenger),
              max_Ped_Peak_Along     = max(Ped_Peak_Along),
              max_Ped_Peak_Total     = max(Ped_Peak_Total),
              max_Bike_Peak_Flow     = max(Bike_Peak_Flow)),
      by = .(ROAD_NO, ID, SLK, Road,
                ped_obs_peak_along, ped_obs_peak_cross, ped_obs_peak_total, ped_24_total_ave,
                bike_obs_peak_along, bike_24_total_ave)]

# Save
fst::write.fst(dfm, path = paste0(saveloc, "PedBike_iRAP_merged.fst"))