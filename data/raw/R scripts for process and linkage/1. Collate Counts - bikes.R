require(openxlsx); require(data.table)
 
# user
system  = Sys.info()
if(system["user"] == "00058985"){
  bdir    = "C:/Users/00058985/OneDrive - UWA/WACRSR/Ped iRAP/"
} else {
  bdir    = "C:/Users//....."
}
 
saveloc = paste0(bdir, "Data/")
folders = c("250303 South West Vulnerable Road Users RESULTS/",
            "250341 Regional Surveys - Kimberley RESULTS/",
            "260335 Vulnerable Users RESULTS/")

COLUMNS = c("TIME_1", "D1_BOUND_1", "D2_BOUND_1", "D_TOTAL_1",
            "TIME_2", "D1_BOUND_2", "D2_BOUND_2", "D_TOTAL_2")

# Loop through files
dfL = list()
for(fx in 1:length(folders)){
  df_folder = list()
  #if(file.exists(paste0(saveloc, folders[fx], "bike_folders.RData"))){
  #  load(paste0(saveloc, folders[fx], "bike_folders.RData")) # df_folder
  #  dfL[[fx]] = df_folder
  #  next
  #}

  files = list.files(paste0(saveloc, folders[fx]), ".xlsm")
  for(ii in 1:length(files)){
    print(paste0(ii, " out of ", length(files)))
    ## What sheets are present
    sheets    = readxl::excel_sheets(paste0(saveloc, folders[fx], files[ii]))

    ## Extract first sheet - details
    dfv       = read.xlsx(paste0(saveloc, folders[fx], files[ii]),
                          startRow = 6,
                          sheet    = "On Road Data")
    names(dfv)[1:12] = COLUMNS

    dfv       = as.data.table(dfv)
    dfv       = dfv[, ..COLUMNS]
    siteids   = tstrsplit(files[ii], "SLK", keep  = 1)[[1]]
    SLKs      = tstrsplit(files[ii], "\\.", keep  = 2)[[1]]
  
    dfv[, file := files[ii]]

    ####
    df_folder[[ii]]   = dfv
  }
  save(df_folder, file = paste0(saveloc, folders[fx], "bike_folders.RData"))
  dfL[[fx]] = df_folder
}
dfbike = rbindlist(lapply(dfL, rbindlist), fill = T)
setnames(dfbike, "TIME_1", "TIME")
dfbike = dfbike[!is.na(TIME)]

# Process
dfbike[, file    := gsub(" - ", " ", file)]
dfbike[, file    := gsub("Fitzroy Crossing", "Fitzroy_Crossing", file)]
dfbike[, file    := gsub("Port Hedland SLK", "Port_Hedland SLK", file)]
dfbike[, file    := gsub("Mt Barker SLK", "Mt_Barker SLK", file)]
dfbike[, file    := gsub("Jurien Bay SLK", "Jurien_Bay SLK", file)]
dfbike[, ID      := tstrsplit(file, "\\.", keep = 1)]
dfbike[, Session := tstrsplit(file, "\\.", keep = 2)]
dfbike[, Session := tstrsplit(Session, " ", keep = 1)]
dfbike[, SLK     := tstrsplit(file, " SLK ", keep = 2)]
dfbike[, SLK     := tstrsplit(SLK, " ", keep = 1)]
dfbike[, Road    := tstrsplit(file, " SLK ", keep = 1)]
dfbike[, Road    := tstrsplit(Road, "^[[:digit:]].\\.[[:digit:]] ", keep = 2)]

dfbike[, Date    := tstrsplit(file, "[[:digit:]]\\.[[:digit:]]. ", keep = 2)]
dfbike[, Date    := gsub(" 2025.xlsm", "", Date)]
dfbike[, Date    := gsub(" 2026.xlsm", "", Date)]
dfbike[, Day     := tstrsplit(Date, " ", keep = 1)]
dfbike[, file    := NULL]
dfbike[, Weekday := Day %notin% "SATURDAY"]

dfbike[, Road    := gsub(" +\\S+$", "", Road)]

# Add road numbers
ROAD_NO = c("Melville Mandurah Hwy"    = "M074",
            "South Western Hwy"        = "H009",
            "Coalfields Hwy"           = "H045",
            "Goodwood Rd"              = "M042",
            "Bussell Hwy"              = "H043",
            "Lakelands Lake Clifton"   = "M074",
            "Pinjarra Rd"              = "M023",
            "Broome Hwy"               = "H042",
            "Victoria Hwy"             = "H011",
            "Derby Hwy"                = "H047",
            "GNH"                      = "H006",
            "Dampier Rd"               = "H046",
            "Port Hedland Rd"          = "H051",
            "Carnarvon Rd"             = "H044",
            "GEH"                      = "H005",
            "Great Eastern Hwy"        = "H005",
            "Goldfields Hwy"           = "H049",
            "Albany Hwy"               = "H001",
            "Great Southern Hwy"       = "M031",
            "South Western Hwy"        = "H009",
            "South Coast Hwy"          = "H008",
            "Brand Hwy"                = "H004",
            "Indian Ocean Dr"          = "M045",
            "Northam Pithara Rd"       = "M032",
            "Williams Narrogin Hwy"    = "H053",
            "Northam Cranbrook Rd"     = "M031",
            "Bindoon Moora Rd"         = "M002",
            "Toodyay Rd"               = "M026",
            "Great Northern Hwy"       = "H006",
            "Midlands Rd"              = "M028",
            "York-Merredin Rd"         = "M041",
            "North West Coastal Hwy"   = "H007",
            "Coolgardie Esperance Hwy" = "M010"
            )
dfbike[, ROAD_NO    := ROAD_NO[Road]]
dfbike[, SLK        := as.numeric(SLK)]
dfbike[, ID         := paste0(ROAD_NO, "-", SLK)]

# Rolling sum to hourly then aggregate counts - previously "_3" was rolling Hourly but not present for all
dfbike[TIME != "24 HOUR", D3_BOUND_3 := frollsum(D1_BOUND_1, 4), by = .(ID, Session)]
dfbike[TIME != "24 HOUR", D4_BOUND_3 := frollsum(D2_BOUND_1, 4), by = .(ID, Session)]
dfbike[TIME != "24 HOUR", D5_BOUND_3 := frollsum(D1_BOUND_2, 4), by = .(ID, Session)]
dfbike[TIME != "24 HOUR", D6_BOUND_3 := frollsum(D2_BOUND_2, 4), by = .(ID, Session)]

# Mean across sessions
dfbike[, along           := D3_BOUND_3 + D4_BOUND_3 + D5_BOUND_3 + D6_BOUND_3]
dfbike[, along_ave       := mean(along, na.rm = T), by = .(ID, TIME)]

# Peak hour
dfbike[, bike_obs_peak_along  := max(along_ave, na.rm = T), by = ID]

# 24 hour stuff, average over session/day
dfbike = dfbike[TIME == "24 HOUR"]
dfbike[, bike_24_total      := D_TOTAL_1 + D_TOTAL_2]
dfbike[, bike_24_total_ave  := mean(bike_24_total, na.rm = T), by = .(ID)]

# Process again
dfbike[, c(grep("TIME_", names(dfbike), value = T)) := NULL]

dfbike  = dfbike[, .(ID, ROAD_NO, Session, SLK, Road, Date, Day, Weekday,
                  bike_obs_peak_along, bike_24_total_ave)]

# Save to file
fst::write.fst(dfbike, path = paste0(saveloc, "Bike_Data.fst"))
