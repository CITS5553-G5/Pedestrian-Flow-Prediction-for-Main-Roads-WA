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

COLUMNS = c("TIME",   "C1_BOUND",   "C2_BOUND",   "C_TOTAL",
        "TIME_1", "D1_BOUND_1", "D2_BOUND_1", "D_TOTAL_1",
        "TIME_2", "D1_BOUND_2", "D2_BOUND_2", "D_TOTAL_2")

# Loop through files
dfL = list()
for(fx in 1:length(folders)){
  df_folder = list()
  #if(file.exists(paste0(saveloc, folders[fx], "ped_folders.RData"))){
  #  load(paste0(saveloc, folders[fx], "ped_folders.RData")) # df_folder
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
                          sheet    = "Pedestrian Data")
    names(dfv)[1:12] = COLUMNS

    dfv       = as.data.table(dfv)
    dfv       = dfv[, ..COLUMNS]
    siteids   = tstrsplit(files[ii], "SLK", keep  = 1)[[1]]
    SLKs      = tstrsplit(files[ii], "\\.", keep  = 2)[[1]]
  
    dfv[, file := files[ii]]

    ####
    df_folder[[ii]]   = dfv
  }
  save(df_folder, file = paste0(saveloc, folders[fx], "folders.RData"))
  dfL[[fx]] = df_folder
}
dfped = rbindlist(lapply(dfL, rbindlist), fill = T)
dfped = dfped[!is.na(TIME)]

# Process
dfped[, file    := gsub(" - ", " ", file)]
dfped[, file    := gsub("Fitzroy Crossing", "Fitzroy_Crossing", file)]
dfped[, file    := gsub("Port Hedland SLK", "Port_Hedland SLK", file)]
dfped[, file    := gsub("Mt Barker SLK", "Mt_Barker SLK", file)]
dfped[, file    := gsub("Jurien Bay SLK", "Jurien_Bay SLK", file)]
dfped[, ID      := tstrsplit(file, "\\.", keep = 1)]
dfped[, Session := tstrsplit(file, "\\.", keep = 2)]
dfped[, Session := tstrsplit(Session, " ", keep = 1)]
dfped[, SLK     := tstrsplit(file, " SLK ", keep = 2)]
dfped[, SLK     := tstrsplit(SLK, " ", keep = 1)]
dfped[, Road    := tstrsplit(file, " SLK ", keep = 1)]
dfped[, Road    := tstrsplit(Road, "^[[:digit:]].\\.[[:digit:]] ", keep = 2)]

dfped[, Date    := tstrsplit(file, "[[:digit:]]\\.[[:digit:]]. ", keep = 2)]
dfped[, Date    := gsub(" 2025.xlsm", "", Date)]
dfped[, Date    := gsub(" 2026.xlsm", "", Date)]
dfped[, Day     := tstrsplit(Date, " ", keep = 1)]
dfped[, file    := NULL]
dfped[, Weekday := Day %notin% "SATURDAY"]

dfped[, Road    := gsub(" +\\S+$", "", Road)]

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
dfped[, ROAD_NO    := ROAD_NO[Road]]
dfped[, SLK        := as.numeric(SLK)]
dfped[, ID         := paste0(ROAD_NO, "-", SLK)]
dfped[, D1_BOUND_2 := as.numeric(D1_BOUND_2)]

# Rolling sum to hourly then aggregate counts - previously "_3" was rolling Hourly but not present for all
dfped[TIME != "24 HOUR", D1_BOUND_3 := frollsum(C1_BOUND,   4), by = .(ID, SLK, Road, Session)]
dfped[TIME != "24 HOUR", D2_BOUND_3 := frollsum(C2_BOUND,   4), by = .(ID, SLK, Road, Session)]
dfped[TIME != "24 HOUR", D3_BOUND_3 := frollsum(D1_BOUND_1, 4), by = .(ID, SLK, Road, Session)]
dfped[TIME != "24 HOUR", D4_BOUND_3 := frollsum(D2_BOUND_1, 4), by = .(ID, SLK, Road, Session)]
dfped[TIME != "24 HOUR", D5_BOUND_3 := frollsum(D1_BOUND_2, 4), by = .(ID, SLK, Road, Session)]
dfped[TIME != "24 HOUR", D6_BOUND_3 := frollsum(D2_BOUND_2, 4), by = .(ID, SLK, Road, Session)]

dfped[, total           := D1_BOUND_3 + D2_BOUND_3 + D3_BOUND_3 + D4_BOUND_3 + D5_BOUND_3 + D6_BOUND_3]
dfped[, total_ave       := mean(total, na.rm = T), by = .(ID, TIME)]
dfped[, ped_obs_peak_total  := max(total, na.rm = T), by = ID]
dfped[, along           := D3_BOUND_3 + D4_BOUND_3 + D5_BOUND_3 + D6_BOUND_3]
dfped[, cross           := D1_BOUND_3 + D2_BOUND_3]
dfped[, along_ave       := mean(along, na.rm = T), by = .(ID, TIME)]
dfped[, cross_ave       := mean(cross, na.rm = T), by = .(ID, TIME)]
dfped[, ped_obs_peak_along  := max(along_ave, na.rm = T), by = ID]
dfped[, ped_obs_peak_cross  := max(cross_ave, na.rm = T), by = ID]

dfped = dfped[TIME == "24 HOUR"]
dfped[, ped_total         := C_TOTAL + D_TOTAL_1 + D_TOTAL_2]
dfped[, ped_24_total_ave  := mean(ped_total, na.rm = T), by = .(ID)]

# Process again
dfped[, c(grep("TIME_", names(dfped), value = T)) := NULL]

dfped  = dfped[, .(ID, ROAD_NO, Session, SLK, Road, Date, Day, Weekday,
                  ped_obs_peak_along, ped_obs_peak_cross, ped_obs_peak_total,
                  ped_24_total_ave)]

# Save to file
fst::write.fst(dfped, path = paste0(saveloc, "Ped_Data.fst"))
