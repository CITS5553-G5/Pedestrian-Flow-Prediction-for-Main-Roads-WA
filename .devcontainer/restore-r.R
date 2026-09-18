# Run from the repository root. The container itself isolates the R library.
lock <- renv::lockfile_read("renv.lock")
if (as.character(getRversion()) != lock$R$Version) {
  stop("Use R ", lock$R$Version, " to restore this environment.")
}
renv::restore(project = getwd(), library = .libPaths(),
              lockfile = "renv.lock", prompt = FALSE, retry = FALSE)
for (record in lock$Packages) {
  actual <- as.character(utils::packageVersion(record$Package))
  if (actual != record$Version) {
    stop(record$Package, ": expected ", record$Version, ", found ", actual)
  }
}
cat("R library matches renv.lock.\n")
