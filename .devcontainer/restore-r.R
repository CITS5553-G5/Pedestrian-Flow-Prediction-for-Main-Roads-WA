# Run from the repository root. The container itself isolates the R library.
lock <- renv::lockfile_read("renv.lock")
if (as.character(getRversion()) != lock$R$Version) {
  stop("Use R ", lock$R$Version, " to restore this environment.")
}
if (!("--check" %in% commandArgs(trailingOnly = TRUE))) {
  args <- list(project = getwd(), library = .libPaths()[1L],
               lockfile = "renv.lock", prompt = FALSE)
  # Older bootstrap versions of renv do not expose the retry argument.
  if ("retry" %in% names(formals(renv::restore))) args$retry <- FALSE
  do.call(renv::restore, args)
}
for (record in lock$Packages) {
  actual <- utils::packageVersion(record$Package)
  if (actual != package_version(record$Version)) {
    stop(record$Package, ": expected ", record$Version, ", found ", actual)
  }
}
cat("R library matches renv.lock.\n")
