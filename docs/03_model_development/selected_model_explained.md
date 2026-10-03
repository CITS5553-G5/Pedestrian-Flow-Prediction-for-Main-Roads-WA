# The Current Pedestrian Flow Model Explained: Yashika's log1p Multiple Linear Regression

This document explains the project's deployed `pedestrian-linear-v1` model: what it predicts, what each part of its equations means, why it was selected, and the conditions under which it is applicable. It follows the [Chinese version](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/docs/03_model_development/selected_model_explained_zh.md>) and is based on the model release, Python inference code, Yashika's Rmd/PDF report, and saved cross-validation results. Source verification date: 2 October 2026.

Coefficients in the equations are rounded to six decimal places for readability. Worked examples use the full precision stored in the release. The release and implementation define the actual model behaviour; this explanation does not modify or retrain the model.

## 1. What exactly is our model?

We use **multiple linear regression on log1p-transformed pedestrian flow**. The model learns coefficients through ordinary least squares (OLS), then transforms predictions back to pedestrians per hour.

“Multiple” means that each prediction depends on several input variables. There are three original input features: the number of commercial buildings identified in imagery, whether footpaths are present on both sides of the road, and the ABS Mesh Block land-use category. After categorical encoding, each model has four predictor columns and an intercept, giving five fitted coefficients.

The project stores **two separately fitted regression models**. The Cross-road model predicts peak pedestrian flow crossing the road, while the Along-road model predicts peak pedestrian flow travelling along it. They use the same inputs but different coefficients. Each minimises its own fitting error; the relationship between the two outputs is not modelled jointly.

| Aspect | Meaning in the current model |
| --- | --- |
| Learning task | Supervised regression: learning continuous predictions from sites with observed survey targets |
| Model structure | Two separately fitted multiple linear regressions, each with an intercept |
| Training method | Ordinary least squares on the `log(1 + y)` scale |
| Regularisation | The selected model has no Ridge or LASSO penalty |
| Target transformation | `log1p(y) = ln(1 + y)`, where `ln` is the natural logarithm |
| Inverse transformation | `expm1(eta) = exp(eta) - 1`, followed by clipping negative values to zero |
| Release identifier | `pedestrian-linear-v1`; the release's model type is `linear_log1p` |
| Execution | R handles training and research validation; Python reads saved coefficients for inference |

A vision model extracts the imagery features, but the model that converts the three features into pedestrian flow is the regression described here. Feature extraction and pedestrian flow prediction are distinct modelling stages.

## 2. What does the model predict?

### 2.1 The two targets and their units

| Meaning | Observed training target | Prediction column | Unit |
| --- | --- | --- | --- |
| Peak pedestrian flow crossing the road | `obs_peak_cross_ped_per_h` | `pred_peak_cross_ped_per_h` | Pedestrians/hour |
| Peak pedestrian flow travelling along the road | `obs_peak_along_ped_per_h` | `pred_peak_along_ped_per_h` | Pedestrians/hour |

`obs` denotes a survey observation and `pred` a model estimate. Predictions are continuous, so a result such as `10.73 pedestrians/hour` is valid: it estimates a flow rate rather than claiming that a survey counted 0.73 of a person. The model does not automatically round predictions to integers.

### 2.2 The precise meaning of “peak”

The project's data contract follows the client's R aggregation logic. Hourly flows are calculated first, then averaged across the three survey days at each time of day. The maximum of the resulting mean hourly profile is taken separately for crossing and along-road movement:

$$
y_t = \max_h\left(\frac{1}{3}\sum_{d=1}^{3} q_{t,d,h}\right),
\qquad t\in\{\text{cross},\text{along}\}.
$$

Here, $q_{t,d,h}$ is the hourly flow for movement type $t$, survey day $d$, and time slot $h$. This is neither an average over all hours across the three days nor an average of the three individual daily maxima.

The crossing and along-road targets take their peaks independently, potentially at different times. Their predictions therefore cannot simply be added and labelled “total pedestrian flow in the same peak hour”. They also do not represent daily totals, real-time counts, or counts at a specific future time. Date, weather, and time of day are not model inputs.

### 2.3 The training sample

The current release records **49 surveyed sites across 28 distinct roads**. These observations have real target values and are separate from the 50 test locations in the current batch prediction input. Obtaining predictions for new batch locations does not make them new training observations.

Table 3 on page 7 of Yashika's PDF shows crossing targets ranging from approximately 0 to 192.33 pedestrians/hour and along-road targets from 0.67 to 349.67. Their medians are approximately 7.33 and 13.00, while their means are 25.39 and 39.87. A small number of busy sites raise the means, consistent with right-skewed target distributions. These ranges describe the historical sample; they are not enforced output limits.

## 3. What do the three input features mean?

| Input field | Meaning and source | Accepted values | Interpretation boundary |
| --- | --- | --- | --- |
| `commercial_buildings` | Number of visible commercial buildings identified under the project's imagery extraction rules | Finite, non-negative numbers; the imagery module returns integers | Does not measure commercial floor area, shop POI counts, or all buildings |
| `footpath_both_sides` | Whether footpaths are identified on both sides of the road | Python booleans or the strings `TRUE` / `FALSE` | `FALSE` means the “both sides” condition is not met; it does not distinguish a single footpath from no footpaths |
| `abs_mb_category_simple` | Simplified land-use category derived from ABS Mesh Block categories | `Residential`, `Other`, or `Commercial` | Describes an area's category, not an individual building's use or population density |

Commercial buildings and footpaths come from imagery; the ABS category comes from a spatial data query. Coordinates, road numbers, and SLK support location resolution, feature extraction, or validation grouping, but do not enter either regression equation. `site_id` identifies a record and is not a predictor.

The observed training range for `commercial_buildings` is **0–12**. Imagery coverage, visibility rules, and counting definitions must remain consistent with training. This input cannot simply be replaced with “commercial POIs within 500 metres” or Microsoft building footprint counts. The current prompt requests clearly visible features and returns `null` when a feature cannot be determined. It does not define the field as a census of commercial buildings within a fixed 500-metre circular buffer.

Complete imagery provenance is limited in the historical training data. Identical field names alone do not establish equivalence between newly extracted values and historical training values. The imagery integration documentation calls for checking this consistency against a reviewed live sample before client delivery.

ABS simplification retains `Residential` and `Commercial` and maps other non-missing original categories to `Other`. At the Python boundary, missing source values remain missing. Yashika's research code also maps missing original ABS categories to `Other`. All 49 training records have non-missing ABS categories, so this boundary improvement does not change their existing classifications.

## 4. From original fields to mathematical variables

The equations use $B$, $F$, $O$, and $C$:

| Symbol | Field or encoding | Value |
| --- | --- | --- |
| $B$ | `commercial_buildings` | Number of commercial buildings |
| $F$ | Indicator for `footpath_both_sides` | 1 for `TRUE`; 0 for `FALSE` |
| $O$ | Indicator for `abs_mb_category_simple == Other` | 1 for `Other`; otherwise 0 |
| $C$ | Indicator for `abs_mb_category_simple == Commercial` | 1 for `Commercial`; otherwise 0 |

The land-use categories are mutually exclusive: a site cannot be both `Other` and `Commercial`. Their encodings are:

| Land-use category | $O$ | $C$ | Interpretation |
| --- | ---: | ---: | --- |
| `Residential` | 0 | 0 | Residential is the reference category |
| `Other` | 1 | 0 | Add the Other coefficient relative to Residential |
| `Commercial` | 0 | 1 | Add the Commercial coefficient relative to Residential |

This is dummy coding of a categorical variable. There is no separate Residential coefficient because its reference effect is included in the intercept. Including indicators for every category together with an intercept would create exact linear dependence among the columns.

Having three original features and four predictor columns is therefore consistent: the land-use feature expands into two columns. These are not four separate data sources.

## 5. The complete equations and their components

### 5.1 The statistical model used in training

For each movement type separately:

$$
z_{i,t}=\ln(1+y_{i,t})
=\beta_{0,t}+\beta_{B,t}B_i+\beta_{F,t}F_i
+\beta_{O,t}O_i+\beta_{C,t}C_i+\varepsilon_{i,t}.
$$

$i$ identifies a surveyed site and $t$ identifies crossing or along-road movement. $y_{i,t}$ is the observed target and $z_{i,t}$ its transformed value. The $\beta$ terms are coefficients learned from data, and $\varepsilon_{i,t}$ represents the discrepancy between the actual transformed target and the modelled relationship.

The intercept $\beta_{0,t}$ is the fitted level for the reference input combination on the logarithmic scale. Each predictor coefficient expresses a difference on that scale while holding other inputs fixed. The error term represents unexplained variation, including omitted travel-demand factors and data noise. A point prediction uses the fitted relationship; it does not generate or randomly add an error term.

### 5.2 The Cross-road model

$$
\eta_{\text{cross}}
=1.440257
+0.261567B
+0.426089F
+0.167629O
+0.072446C.
$$

$$
\boxed{\hat y_{\text{cross}}=\max\{\exp(\eta_{\text{cross}})-1,\;0\}}
$$

### 5.3 The Along-road model

$$
\eta_{\text{along}}
=1.980243
+0.296192B
+0.272677F
+0.119303O
-0.107338C.
$$

$$
\boxed{\hat y_{\text{along}}=\max\{\exp(\eta_{\text{along}})-1,\;0\}}
$$

$\eta$ is the initial linear prediction on the `log(1 + flow)` scale, not in pedestrians/hour. $\exp$ is the exponential function with base $e$. Subtracting 1 reverses the addition of 1 in the target transformation; the outer `max` ensures non-negative predictions.

`log1p` and `expm1` are numerical functions for `ln(1 + y)` and `exp(eta) - 1`, respectively. They support stable calculation near zero and introduce no additional learned parameters.

### 5.4 Why add 1, take logarithms, and transform back?

Zero flow can occur, but `ln(0)` has no finite value. Using `ln(1 + y)` maps a zero target to zero, allowing zero observations to remain in the data.

The logarithm compresses differences between large and small flows. For example, 0, 10, 100, and 300 pedestrians/hour become approximately 0, 2.398, 4.615, and 5.707. This reduces the numerical influence of very busy sites in the training loss compared with fitting squared errors directly on the original scale. It does not guarantee removal of skewness, heteroscedasticity, or outlier effects; these still require diagnosis.

The inverse transformation returns predictions to pedestrians/hour for comparison with survey observations. The report's RMSE, MAE, and $R^2$ are all calculated on this original scale.

### 5.5 Why is it linear regression if the inverse transformation is exponential?

“Linear” describes the additive relationship between the transformed target and the coefficients: $\eta$ is an intercept plus weighted input terms. After transformation back to the original flow scale, predictions vary exponentially with $B$, so that relationship is no longer a straight line.

The current equations contain no squared terms, thresholds, or interactions. For example, there is no $B\times F$ term, so the slope of commercial building count on the $\eta$ scale does not change with footpath status. This simple structure supports interpretation but limits the complexity of environmental relationships the model can express.

The model differs from Poisson or negative binomial count regression, which specifies a corresponding probability distribution and link function for the original counts or flow. This project transforms the target first and fits `lm()`; it does not use a Poisson likelihood. It is also different from logistic regression for binary outcome probabilities.

## 6. How should the coefficients be interpreted?

### 6.1 The intercept is not a guaranteed minimum observed flow

When $B=0$, $F=0$, and the land-use category is Residential, every predictor term is zero. The crossing prediction is approximately $\exp(1.440257)-1=3.22$ pedestrians/hour, and the along-road prediction is approximately $\exp(1.980243)-1=6.24$ pedestrians/hour.

These estimates refer to a particular reference combination. They are not guaranteed minimum real-world flows and do not imply that those numbers of pedestrians must exist when commercial buildings are absent. Observed crossing targets can be zero. Given this release's input restrictions and coefficients, its minimum prediction over valid inputs is approximately 3.22 for crossing and 5.51 for along-road movement. The latter occurs at $B=0$, $F=0$, and Commercial. Consequently, zero clipping does not actually activate for valid inputs in this release, and the model cannot predict exactly zero flow. The along-road minimum differs from its Residential reference prediction because its Commercial coefficient is negative.

### 6.2 What do positive and negative coefficients mean?

Holding other inputs fixed, a positive coefficient increases $\eta$ and therefore the predicted flow after exponentiation. A negative coefficient decreases the prediction. The negative Commercial coefficient in the along-road model represents a fitted difference relative to Residential after controlling for imagery-derived commercial building count and footpath status.

This does not establish that commercial areas cause lower pedestrian flows. Land-use category and commercial building count measure different things and may be correlated. The coefficients also come from a small sample, and category effects have substantial uncertainty. These are conditional predictive relationships, not causal effects of planning interventions.

### 6.3 Coefficients imply multipliers, not fixed additions of pedestrians

When zero clipping does not apply, an input change that increases $\eta$ by $\Delta$ gives:

$$
\hat y_{\text{new}}+1
=\exp(\Delta)(\hat y_{\text{old}}+1).
$$

The exponentiated coefficient therefore multiplies **“predicted flow + 1”**.

| Change, holding other inputs fixed | Crossing coefficient | Crossing multiplier | Along-road coefficient | Along-road multiplier |
| --- | ---: | ---: | ---: | ---: |
| Add one commercial building | 0.261567 | 1.2990 | 0.296192 | 1.3447 |
| Change footpath status from FALSE to TRUE | 0.426089 | 1.5313 | 0.272677 | 1.3135 |
| Change Residential to Other | 0.167629 | 1.1825 | 0.119303 | 1.1267 |
| Change Residential to Commercial | 0.072446 | 1.0751 | −0.107338 | 0.8982 |

Each additional commercial building multiplies “prediction + 1” by approximately 1.299 for crossing, an increase of about 29.9%, and by approximately 1.345 for along-road movement, an increase of about 34.5%. It does not add a fixed 0.2616 pedestrians/hour. Nor is 29.9% exactly the percentage increase in the unshifted flow: the two interpretations become close only when flow is large relative to 1.

The increase on the original scale is $(\exp(\Delta)-1)(\hat y_{\text{old}}+1)$. The same coefficient therefore produces different absolute changes at low-flow and high-flow sites. This also explains why building counts far outside the training range can produce large exponential extrapolations.

### 6.4 Coefficient size, significance, and predictive value

Building-count coefficients cannot be directly compared with categorical coefficients to establish a strict feature-importance ranking. One describes a one-building increment, while another describes a complete category change; their units and ranges differ.

In Table 13 on page 33 of Yashika's PDF, commercial building count has a p-value below 0.001 in both models. Footpath status and both land-use indicators have p-values above 0.05. Under the table's conventional regression inference, evidence for the latter coefficients is weaker. This does not automatically justify deleting them, and a p-value is not a confidence score for an individual prediction. Displayed values of `0.0000` are rounded to four decimal places, not literally zero probabilities.

The table uses `summary(lm)` and does not provide standard errors adjusted for clustering by road. Grouped cross-validation does not automatically make coefficient inference cluster-robust. Observations from the same road may be related, so this table alone should not support strong statistical or causal claims.

## 7. A complete worked example

Suppose a site has two identified commercial buildings, footpaths on both sides, and a simplified ABS category of Commercial. Its encoding is $B=2$, $F=1$, $O=0$, and $C=1$.

For crossing:

$$
\eta_{\text{cross}}
=1.440257+0.261567\times2+0.426089+0.072446
\approx2.461926.
$$

$$
\hat y_{\text{cross}}=\exp(2.461926)-1\approx10.73\text{ pedestrians/hour}.
$$

For along-road movement:

$$
\eta_{\text{along}}
=1.980243+0.296192\times2+0.272677-0.107338
\approx2.737965.
$$

$$
\hat y_{\text{along}}=\exp(2.737965)-1\approx14.46\text{ pedestrians/hour}.
$$

Changing only the commercial building count from two to three gives approximately 14.23 pedestrians/hour for crossing and 19.78 for along-road movement, calculated using the full-precision coefficients. This illustrates the equations; it is neither a survey observation nor a validation of predictive performance.

## 8. How was the model trained, and why was it selected?

### 8.1 What training actually optimises

Each movement type solves its own objective:

$$
\hat{\boldsymbol\beta}_t
=\arg\min_{\boldsymbol\beta_t}
\sum_{i\in\mathcal T}
\left[\ln(1+y_{i,t})-
(\beta_{0,t}+\beta_{B,t}B_i+\beta_{F,t}F_i+\beta_{O,t}O_i+\beta_{C,t}C_i)\right]^2.
$$

$\mathcal T$ is the current training set: the training sites in one cross-validation split, or all 49 approved survey sites for the final fit. The objective minimises squared errors on the logarithmic scale, not MAE or RMSE on the original pedestrians/hour scale.

The R code calls `lm(formula, data = train_p)` without observation weights or regularisation. The official R documentation states that `lm()` uses ordinary least squares when `weights` is not specified. There is no road-level weighting here; multiple sites on one road remain individual fitting observations. [Official R `lm` documentation](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/lm.html)

### 8.2 Selection used performance under a shared validation design

Yashika compared a median baseline, parsimonious linear regression, Ridge, LASSO, Random Forest, and Gradient Boosting. The selected linear model uses three interpretable original features, while other methods can use the wider candidate feature set. Consequently, the comparison evaluates each method together with its feature configuration; it is not strictly an experiment that keeps every input identical and changes only the algorithm.

For each target, models are ranked separately on $R^2$, RMSE, and MAE. The six ranks across the two targets are then averaged to obtain the overall ranking. The saved results are:

| Prediction approach | Average rank, lower is better | Mean $R^2$ across the two targets | Mean RMSE (pedestrians/hour) | Mean MAE (pedestrians/hour) |
| --- | ---: | ---: | ---: | ---: |
| Linear regression | 1.000 | 0.572 | 33.08 | 17.72 |
| Random Forest | 2.000 | 0.354 | 43.74 | 24.95 |
| Gradient Boosting | 3.833 | 0.141 | 49.25 | 28.68 |
| Ridge | 4.167 | −0.101 | 56.58 | 26.83 |
| LASSO | 4.833 | −1.271 | 84.90 | 32.67 |
| Median baseline | 5.167 | −0.191 | 58.79 | 27.90 |

The current linear approach ranks first on all three metrics for both targets, giving an overall average rank of 1. This result applies to the project's sample and evaluated configurations; it does not prove that linear regression outperforms tree models on every road or at every sample size. Fewer parameters may help reduce fitting variability in a small sample, but that is a plausible interpretation rather than a mechanism established independently by this comparison.

“Parsimonious” refers to a relatively simple structure and few features. It does not mean that the model merely predicts an average or that its features were automatically selected through LASSO.

## 9. How should the validation results be read?

### 9.1 Five-fold cross-validation grouped by road

All sites sharing a `road_no` are assigned to the same fold. In each round, four folds train the models and the remaining fold supplies the held-out roads for prediction. Repeating this five times produces one out-of-fold (OOF) prediction per site, generated without training on that site's road.

This reduces leakage from placing different sites on the same road in both training and validation, and better approximates prediction on roads excluded from training. It does not establish external validation in a new city, season, or entire road network, and it does not remove possible spatial relationships between different roads.

Numeric imputation medians, categorical imputation modes, and known category levels are learned within each training fold before being applied to its validation fold. Validation observations do not determine these imputation rules.

### 9.2 Results for the two targets

| Target | OOF $R^2$ | RMSE (pedestrians/hour) | MAE (pedestrians/hour) | Median absolute error (pedestrians/hour) |
| --- | ---: | ---: | ---: | ---: |
| Cross-road | 0.4246 | 29.14 | 15.18 | 4.74 |
| Along-road | 0.7188 | 37.02 | 20.26 | 8.84 |

$R^2=1-\sum_i(y_i-\hat y_i)^2/\sum_i(y_i-\bar y)^2$. The report calculates metrics after pooling the OOF predictions. $R^2$ measures the improvement in squared error relative to the evaluation sample's mean reference; it is **not an accuracy percentage**. An along-road $R^2$ of 0.7188 does not mean that predictions have a 71.88% probability of being correct. A negative $R^2$ means squared error exceeds that of this mean reference.

RMSE is the square root of mean squared error and gives greater influence to large errors. MAE is the mean absolute error. A crossing MAE of 15.18 means that the average absolute deviation in these OOF predictions is approximately 15.18 pedestrians/hour; it does not guarantee that each new site's error will fall within that amount.

Median absolute error is lower than MAE, while RMSE exceeds MAE, indicating that some larger errors influence the error distribution. This is consistent with a few busy sites affecting overall evaluation in a small sample, but does not establish an error bound for an individual site.

Along-road $R^2$ is higher even though its MAE and RMSE are larger in original units. This is not contradictory: along-road targets vary more, so relative squared-error performance can improve while absolute errors remain larger.

### 9.3 What does the road-level bootstrap show?

The report resamples complete roads from the existing OOF predictions 1,000 times and uses the 2.5th and 97.5th percentiles of the metrics to form 95% intervals. The current linear model's intervals are:

| Target | Bootstrap interval for $R^2$ | Bootstrap interval for RMSE (pedestrians/hour) | Bootstrap interval for MAE (pedestrians/hour) |
| --- | --- | --- | --- |
| Cross-road | [−0.135, 0.635] | [16.75, 38.74] | [7.99, 21.00] |
| Along-road | [−0.083, 0.840] | [15.62, 51.27] | [10.50, 28.62] |

These intervals describe variation in overall evaluation metrics under the current road sample. Both $R^2$ intervals cross zero, indicating substantial performance uncertainty under limited road coverage. They are not prediction intervals for a new site, nor do they mean that a crossing prediction should have 16.75–38.74 added or subtracted from it.

This bootstrap resamples fixed OOF results. It does not retrain or reselect a model in each resample and therefore does not capture all uncertainty arising from model selection and changes in training.

### 9.4 Remaining validation limitations

Sites on the same road are not necessarily independent, and having only 28 roads limits generalisation evidence. The comparison corresponds to the report's single grouped five-fold configuration. Once the final model is fitted on all observations, its fitted errors on those same sites cannot be treated as new generalisation results.

The approach was selected using the same cross-validation results; the report does not provide an entirely independent final test set after selection. If feature choices were informed by EDA on the full dataset, that selection was not nested as a complete procedure inside the outer validation. Grouping and fold-specific imputation reduce road leakage and imputation leakage, but do not establish external performance free of every selection bias.

The project's data contract also requires a sensitivity evaluation excluding the two sites whose targets were corrected, `250341-04` and `260335-38`. The Yashika Rmd and release results checked for this explanation do not provide those sensitivity results. This document therefore does not count that evaluation as completed; it should be addressed separately in subsequent formal reporting.

## 10. Main characteristics and statistical assumptions

### 10.1 Interpretability, few inputs, and inexpensive inference

Each output decomposes into an intercept and four encoded predictor terms, allowing direct inspection of coefficients and directions. Prediction involves multiplication, addition, and exponentiation. After loading, it requires neither retraining nor an R installation at Python runtime. The complete site prediction workflow still includes location resolution, imagery, and ABS feature extraction, so regression calculation time alone does not describe end-to-end runtime.

The regression is deterministic: the same release and effective inputs produce the same results. Two sites with identical values for the three features receive identical predictions, even if their locations differ. Road identity, historical flow, and date do not enter the model to distinguish them.

### 10.2 Additive structure, conditional association, and limited flexibility

Effects add on the logarithmic scale and multiply the corresponding “flow + 1” on the original scale. Commercial building count has a fixed slope, while categories provide fixed offsets. The model does not automatically learn changes beyond building-count thresholds or interactions between building count and footpath status.

The relationship is a conditional association between site environment and flow. Changing an input and recalculating shows how the model changes its prediction, not the true causal effect of a road intervention.

### 10.3 Estimating coefficients and making statistical inferences are different

OLS can calculate coefficients without normally distributed residuals. Interpreting those coefficients as stable relationships without systematic bias requires examining the transformed conditional relationship, potentially important omitted factors correlated with the inputs, and severe collinearity.

Conventional `summary(lm)` standard errors, p-values, and intervals rely on stronger error assumptions concerning independence, variance structure, and relevant distributional conditions. Log transformation and grouped validation do not automatically establish these assumptions. Imagery recognition error, relationships within roads, and small samples can affect inference.

### 10.4 The current inverse transformation has no mean bias adjustment

In general, $\exp(E[Z\mid X])-1$ is not equal to $E[\exp(Z)-1\mid X]$. Consequently, fitting the logarithmic target does not automatically make `exp(eta) - 1` the conditional mean of original-scale flow. If conditional log-scale residuals are symmetric and the fitted relationship is correct, direct back-transformation is closer to the conditional median. [Hyndman and Athanasopoulos on transformations and back-transformation](https://otexts.com/fpp3/ftransformations.html)

Under the additional assumptions $Z=\eta+\varepsilon$ and $\varepsilon\mid X\sim N(0,\sigma^2)$, the theoretical mean before considering clipping is $\exp(\eta+\sigma^2/2)-1$. This hypothetical formula explains the distinction; **it is not the prediction formula implemented in this project**, nor does this document claim that the residuals satisfy that distribution.

The current release does not apply a smearing factor or add $\sigma^2/2$. Changing the inverse transformation changes predictions and should be evaluated as a new approach through grouped validation, rather than by editing existing coefficients or adding a multiplier in the frontend.

## 11. Applicability and boundaries of use

### 11.1 Conditions that provide stronger support for use

The current model is better supported as a baseline for sites within the Western Australian project context whose road environments and survey target definitions resemble those represented in training. New sites should have reviewable inputs consistent with training definitions, preferably with commercial building counts in the observed 0–12 range. Even within that range, the setting still requires consideration of historical sample coverage.

The model can support initial site screening, inspection of estimated relative flow differences, prioritisation of further surveys, and batch generation of both peak-flow estimates under consistent definitions. Prediction error also affects site rankings: nearby predicted values do not automatically indicate a real difference in flow.

### 11.2 Uses that require additional evidence

| Setting or use | Boundary of the current model |
| --- | --- |
| Busy commercial centres, stations, or major event sites absent from training | Three inputs may not describe their distinctive pedestrian demand; further surveys and validation are needed |
| Commercial building counts far above 12 | Exponential extrapolation may grow rapidly; the code warns about the range but does not automatically cap predictions |
| Different cities, countries, or road systems | Transferability cannot be assumed; external validation is required |
| Weather, holidays, seasonal changes, or real-time variation | The equations have no corresponding inputs and do not form a time-series model |
| Estimating the increase after footpath construction | Associational coefficients do not replace causal intervention evaluation |
| Daily totals or flow at a specific hour | Training targets are separately aggregated peak-hour measures |
| Summing predictions across sites or movement types | Overlapping pedestrians, peak timing, spatial definitions, and back-transformed means require consideration |
| Treating predictions as surveys, safety ratings, or crash risk | The model estimates pedestrian flow and does not directly predict those other outcomes |
| Providing a site-specific uncertainty interval or probability guarantee | The release returns point predictions and status/warnings, not site-level prediction intervals |

A building count within 0–12 satisfies only a simple range check; it does not prove that a site lies within the model's supported distribution. A rural road and a busy transport hub might each have two commercial buildings, yet their true demand may differ in ways that the three inputs cannot capture.

### 11.3 Changes in feature sources also affect applicability

Missing imagery, obstruction, capture dates, changes in the recognition model, image sampling offsets, and repeated building counts can affect the imagery inputs. ABS categories depend on spatial matching and data vintage. Unchanged regression coefficients do not guarantee unchanged performance of the entire prediction system.

R/Python numerical equivalence, consistency of imagery extraction, and generalisation to new sites therefore answer different questions: whether the equations are implemented consistently, whether inputs retain the same meaning, and whether actual new sites are predicted well. Passing the first check does not replace the other two.

## 12. How the system uses the model

### 12.1 From a submitted location to predictions

```mermaid
flowchart LR
    A[Input site and location information] --> B[Resolve and validate location]
    B --> C[Extract building count and footpath status]
    B --> D[Query and simplify ABS category]
    C --> E[Align and validate three features]
    D --> E
    E --> F[Load release coefficients and calculate both eta values]
    F --> G[Apply expm1 and non-negative clipping]
    G --> H[Return both flow predictions and status information]
```

Coordinates or road number/SLK resolve the position used to query features. Once records are aligned by `site_id`, `model.py` reads the intercepts, numeric coefficients, and category effects from JSON, calculates both $\eta$ values, and applies `max(math.expm1(eta), 0.0)`.

`model_version`, `status`, and `warnings` record the release, input processing, and range checks; they are not additional prediction targets. `status=ok` means the relevant processing checks passed, not that prediction error is small or that the site has been validated in the field.

### 12.2 How missing values are handled

The model layer validates inputs strictly by default. Missing features, unknown simplified categories, negative or non-finite building counts, invalid boolean formats, and missing or duplicate identifiers trigger contract errors. A site without available imagery is not silently treated as having zero commercial buildings and no footpaths.

The model layer separately offers explicit `allow_fallback=True` for reviewed calls that permit replacements from the original R preprocessing:

| Eligible replacement case | Saved replacement | Recording |
| --- | --- | --- |
| Missing commercial building count | Training median: 2 | Row-level warning |
| Missing footpath status | Training mode: FALSE | Row-level warning |
| Missing or unknown simplified ABS category | Training mode: Residential | Row-level warning |

Fallback does not permit negative values, infinities, or invalid boolean formats, and cannot disguise service failures as valid observations. The unified site prediction service currently does not use this fallback: incomplete imagery features block a formal prediction for that site while retaining status information. Stored medians and modes in the JSON do not mean that the formal workflow always imputes missing inputs.

Building counts above 12 trigger an extrapolation warning rather than being clipped to 12; the supplied value still enters the equation. Negative building counts are invalid inputs and do not proceed with a warning alone.

### 12.3 The relationship between R and Python

The Rmd reads training data, processes features, runs grouped comparisons, fits final models on all observations, and saves an RDS bundle. The exporter reads that existing bundle and writes parameters and preprocessing information to JSON without retraining. Python inference requires only the release and input features.

Existing R reference cases cover all 49 training sites, 24 synthetic input combinations, and six fallback cases, giving 79 cases. Tests compare Python results against R's `predict.lm` reference predictions with absolute tolerance `1e-12` and relative tolerance `1e-13`. This verifies software reproduction, not prediction ability on new roads, and must not replace OOF performance results.

Expanding the sample, reselecting features, or changing the inverse transformation requires a new model version, export, and verification. Coefficients must not be edited manually while retaining `pedestrian-linear-v1` and its old evaluation metrics.

## 13. Where are the equations, report, and implementation?

The links below point to files in this workspace. PDF page references use the page numbers printed at the bottom of the document; the report has 42 pages.

| File | Contents | Location or purpose |
| --- | --- | --- |
| [Yashika PDF report](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/03_model_development/03_Yashika_Predict_Pedestrians_Final_Model_Comparison.pdf>) | Rendered research report, code, coefficients, and validation results | Page 7, Table 3: target distributions; pages 13–14: equation and inverse-transformation code; page 21, Table 8: overall ranking; section 22 begins on page 32, and page 33, Table 13 contains both models' coefficients |
| [Yashika Rmd source](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/03_model_development/03_Yashika_Predict_Pedestrians_Final_Model_Comparison.Rmd>) | Complete training, preprocessing, validation, and saving logic | `linear_features`, `fit_linear`, `predict_linear`, `model-ranking`, and `linear-coefficients` code blocks |
| [Model release JSON](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/src/pedflow/modeling/releases/pedestrian_linear_v1.json>) | Full-precision parameters used at runtime | `models.cross`, `models.along`, preprocessing, training range, provenance, and evaluation |
| [Python model implementation](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/src/pedflow/modeling/model.py>) | Validation, category mapping, linear prediction, and inverse transformation | `simplify_abs_categories`, `PedestrianFlowModel.predict`, and `load_model` |
| [R model bundle](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/06_outputs/03_model_development/03_yashika_model_comparison/03_pedestrian_flow_final_model_bundle.rds>) | Fitted R model objects and research information | Source of model parameters in the release JSON |
| [R exporter](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/tools/export_linear_model.R>) | Exports saved parameters and generates independent R reference predictions | Reproduces the export without retraining |
| [Model integration guide](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/docs/03_model_development/selected_model_integration.md>) | API usage, input contracts, export commands, and R/Python verification | Detailed engineering integration instructions |
| [Data contracts](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/docs/01_data_preparation/haoqi-shared_data_tables.md>) | Target aggregation, the 49-site research table, and prediction input/output definitions | Target definitions and data boundaries |
| [Imagery integration guide](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/docs/02_feature_extraction/imagery_integration.md>) | Current imagery extraction process and provenance limitations | Feature consistency, missing data handling, and review requirements |
| [Imagery prompt](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/src/pedflow/imagery/prompts/notebook_v1.txt>) | Rules for extracting visible commercial buildings, footpaths, and other features | Return null when undetermined, follow counting rules, and disregard repeated images |
| [OOF metrics CSV](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/06_outputs/03_model_development/03_yashika_model_comparison/03_model_comparison_cv_metrics.csv>) | Four performance metrics for each model and target | Original values for the results in section 9 |
| [Overall ranking CSV](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/06_outputs/03_model_development/03_yashika_model_comparison/03_model_comparison_overall_ranking.csv>) | Overall rankings for the six approaches | Original values for the comparison in section 8 |
| [Bootstrap intervals CSV](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/06_outputs/03_model_development/03_yashika_model_comparison/03_model_comparison_bootstrap_ci.csv>) | Metric intervals from road-level resampling | Original values for section 9.3 |
| [R reference cases](</Users/haoqi/Nexus/09_Workspace/CITS5553 - Data Science Capstone Project/03_Project/tests/fixtures/modeling/r_linear_reference.json>) | Reference inputs and outputs for checking Python reproduction | Software equivalence verification, not generalisation evaluation |

**The Rmd does not need to be rerun to inspect the model.** The existing PDF already contains equation code and complete coefficient tables, although it does not substitute all values into a single mathematical equation as this document does. Reported coefficients are rounded to four decimal places; the release JSON provides full runtime precision. Running the Rmd is needed when retraining or regenerating the research report.

## 14. Suggested wording for a report or presentation

> This project uses two separately fitted parsimonious multiple linear regression models to predict peak-hour pedestrian flow crossing and travelling along the road. Inputs are imagery-derived commercial building count, footpath presence on both sides, and a simplified ABS land-use category. Observed flow is transformed using log1p, fitted by ordinary least squares, and converted back to pedestrians per hour using expm1. On a dataset of 49 sites across 28 roads, the approach achieved the best aggregate ranking among six evaluated prediction approaches under road-grouped five-fold cross-validation. Out-of-fold R² values were 0.425 for crossing and 0.719 for along-road movement; these are goodness-of-fit measures, not accuracy percentages. Given the sample size, road coverage, and feature provenance limitations, the release should be treated as a deployment baseline requiring continued external validation. Its coefficients describe predictive associations rather than causal effects.
