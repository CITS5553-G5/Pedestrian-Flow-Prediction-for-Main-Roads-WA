# Export the selected fitted models; never retrain or execute the research notebook.
# Usage: Rscript --vanilla tools/export_linear_model.R BUNDLE DATASET RELEASE REFERENCES
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4L) {
  stop("Expected BUNDLE.rds DATASET.xlsx RELEASE.json REFERENCES.json")
}
if (!requireNamespace("jsonlite", quietly = TRUE) ||
    !requireNamespace("readxl", quietly = TRUE)) {
  stop("The export requires jsonlite and readxl in the project R environment.")
}

bundle <- readRDS(args[1])
stopifnot(identical(bundle$selected_model, "Linear regression"))
features <- c("commercial_buildings", "footpath_both_sides", "abs_mb_category_simple")
factors <- features[-1]
fits <- lapply(bundle$final_models[c("Cross", "Along")], function(x) x$linear)
dat <- as.data.frame(readxl::read_excel(args[2], sheet = "Model_Data"))
dat$abs_mb_category_simple <- ifelse(
  dat$abs_mb_category_2021 %in% c("Residential", "Commercial"),
  dat$abs_mb_category_2021, "Other"
)
dat$commercial_buildings <- as.numeric(gsub(",", "", dat$commercial_buildings))
dat$footpath_both_sides <- as.character(dat$footpath_both_sides)
stopifnot(!anyNA(dat[features]), !anyDuplicated(dat$site_id))

# Replay the saved preprocessing for just the approved linear-model features.
prepare <- function(data, fit) {
  out <- data[features]
  v <- "commercial_buildings"
  out[[v]][is.na(out[[v]])] <- fit$prep$medians[[v]]
  for (v in factors) {
    x <- as.character(out[[v]])
    known <- fit$prep$levels[[v]]
    fallback <- fit$prep$modes[[v]]
    x[is.na(x) | x == ""] <- fallback
    x[!x %in% known] <- fallback
    out[[v]] <- factor(x, levels = known)
  }
  out
}

models <- list()
for (name in names(fits)) {
  fit <- fits[[name]]
  target <- bundle$targets[[if (name == "Cross") "Cross-road" else "Along-road"]]
  stopifnot(identical(fit$features, features), inherits(fit$model, "lm"))
  stopifnot(identical(all.vars(formula(fit$model)), c(target, features)))
  stopifnot(identical(as.character(formula(fit$model)[[2]][[1]]), "log1p"))
  stopifnot(all(unlist(fit$model$contrasts) == "contr.treatment"))
  stopifnot(nrow(dat) == nobs(fit$model))
  prepared <- prepare(dat, fit)
  # Prevent attaching a changed training workbook to an older fitted release.
  for (v in features) {
    stopifnot(isTRUE(all.equal(
      as.character(prepared[[v]]), as.character(fit$model$model[[v]])
    )))
  }
  stopifnot(isTRUE(all.equal(log1p(dat[[target]]), fit$model$model[[1]])))
  stopifnot(identical(fit$prep, fits$Cross$prep))
  stopifnot(identical(fit$model$xlevels, fits$Cross$model$xlevels))

  beta <- coef(fit$model)
  expected_terms <- c("(Intercept)", features[1], unlist(lapply(factors, function(v) {
    paste0(v, fit$model$xlevels[[v]][-1])
  })))
  stopifnot(identical(names(beta), expected_terms), all(is.finite(beta)))
  effects <- setNames(lapply(factors, function(v) {
    levels <- fit$model$xlevels[[v]]
    values <- c(0, unname(beta[paste0(v, levels[-1])]))
    as.list(setNames(values, levels))
  }), factors)
  models[[tolower(name)]] <- list(
    target = target,
    prediction_column = sub("^obs_", "pred_", target),
    intercept = unname(beta["(Intercept)"]),
    commercial_buildings_coefficient = unname(beta["commercial_buildings"]),
    categorical_effects = effects
  )
}

fit <- fits$Cross
release <- list(
  schema_version = 1L,
  model_version = "pedestrian-linear-v1",
  model_type = "linear_log1p",
  features = features,
  prediction_units = "pedestrians_per_hour",
  inverse_transform = "max(expm1(eta), 0)",
  numeric_preprocessing = list(commercial_buildings = list(
    median = unname(fit$prep$medians["commercial_buildings"]),
    training_min = min(dat$commercial_buildings),
    training_max = max(dat$commercial_buildings)
  )),
  categorical_preprocessing = setNames(lapply(factors, function(v) {
    list(levels = fit$model$xlevels[[v]], mode = unname(fit$prep$modes[v]))
  }), factors),
  models = models,
  provenance = list(
    source_bundle = basename(args[1]),
    source_bundle_md5 = unname(tools::md5sum(args[1])),
    training_dataset = basename(args[2]),
    training_dataset_md5 = unname(tools::md5sum(args[2])),
    training_observations = nrow(dat),
    training_roads = length(unique(dat$road_no)),
    export_runtime = R.version.string,
    exporter = "tools/export_linear_model.R"
  ),
  evaluation = list(
    method = "road_no grouped five-fold out-of-fold cross-validation",
    metrics = bundle$grouped_cv_performance[
      bundle$grouped_cv_performance$Model == "Linear regression", ]
  )
)

# R predict.lm is the independent reference, not a second coefficient calculation.
cases <- dat[c("site_id", features)]
cases$case_kind <- "training"
grid <- expand.grid(
  commercial_buildings = unique(c(0, 2, max(dat$commercial_buildings),
                                  max(dat$commercial_buildings) + 1)),
  footpath_both_sides = c("FALSE", "TRUE"),
  abs_mb_category_simple = c("Residential", "Other", "Commercial"),
  stringsAsFactors = FALSE
)
grid$site_id <- paste0("grid-", seq_len(nrow(grid)))
grid$case_kind <- "category_grid"
cases <- rbind(cases, grid[names(cases)])
edge <- grid[rep(1, 6), names(cases)]
edge$site_id <- paste0("fallback-", seq_len(nrow(edge)))
edge$case_kind <- "fallback"
edge$commercial_buildings[c(1, 4)] <- NA_real_
edge$footpath_both_sides[c(2, 4)] <- NA_character_
edge$abs_mb_category_simple[c(3, 4)] <- NA_character_
edge$abs_mb_category_simple[5] <- "Unseen"
edge$abs_mb_category_simple[6] <- ""
cases <- rbind(cases, edge)
for (name in names(fits)) {
  fit <- fits[[name]]
  column <- models[[tolower(name)]]$prediction_column
  cases[[column]] <- pmax(expm1(as.numeric(predict(
    fit$model, newdata = prepare(cases, fit)
  ))), 0)
}

for (path in args[3:4]) dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
jsonlite::write_json(release, args[3], pretty = TRUE, auto_unbox = TRUE, digits = 17)
exported <- jsonlite::read_json(args[3], simplifyVector = FALSE)
for (name in names(fits)) {
  beta <- coef(fits[[name]]$model)
  model <- exported$models[[tolower(name)]]
  stopifnot(identical(model$intercept, unname(beta["(Intercept)"])))
  stopifnot(identical(model$commercial_buildings_coefficient,
                      unname(beta["commercial_buildings"])))
  for (v in factors) {
    for (level in fits[[name]]$model$xlevels[[v]][-1]) {
      stopifnot(identical(model$categorical_effects[[v]][[level]],
                          unname(beta[paste0(v, level)])))
    }
  }
}
rownames(cases) <- NULL
jsonlite::write_json(list(
  model_version = release$model_version,
  source_bundle_md5 = release$provenance$source_bundle_md5,
  reference_method = "R stats::predict.lm with saved preprocessing, expm1 and pmax",
  cases = cases
), args[4], pretty = TRUE, auto_unbox = TRUE, digits = 17, na = "null")
cat("Exported two fitted models and", nrow(cases), "R reference cases.\n")
