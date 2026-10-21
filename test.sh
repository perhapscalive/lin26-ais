#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Use a Python 3.13-compatible scikit-learn that can load the 1.4.0 pickles.
# Supply it without changing uv.lock; newer releases cannot load these assets.
# Let the input climate file determine the sample count (--nsamps only validates).
uv run --frozen --with 'scikit-learn==1.5.2' lin26-ais main \
  --scenario ssp245 \
  --climate-data-file fair_temperature_runs/output/ssp245/gsat.nc \
  --scheme posterior \
  --seed 42 \
  --baseyear 2015 \
  --pyear-start 2015 --pyear-end 2100 --pyear-step 1 \
  --mean-model-file data/models/mean_model.pkl \
  --lower-model-file data/models/lower_model.pkl \
  --upper-model-file data/models/upper_model.pkl \
  --posterior-samples-file data/posterior/posterior_samples.csv \
  --posterior-weights-file data/posterior/posterior_weights.npy \
  --output-ais-gslr-file outputs/quick_tests/ssp245_posterior/ais-gslr.nc \
  --output-diagnostics-file outputs/quick_tests/ssp245_posterior/lin26-diagnostics.nc
