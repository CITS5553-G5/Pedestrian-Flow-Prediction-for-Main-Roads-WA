# Historical context configuration

`context_features_v1.json` preserves the previous six-source research settings
unchanged. It supports reproducing candidate features used during model comparison;
it is not the default prediction configuration. Google Places Aggregate remains
disabled and excluded under the existing project decision.

The health and education notebooks explicitly read this historical configuration.
Other retained research source modules can still be called directly. A research
caller using `build_context_features` must explicitly supply its source registry;
the default registry and command-line workflow accept ABS only. Pointing the formal
command at this six-source configuration fails before any source performs I/O.

The active configuration is `configs/context_features_v1.json`, version
`context_abs_v1`. The pre-change snapshot is locally archived under
`07_test/context_before_abs_20260920/`; that directory is ignored by Git.
