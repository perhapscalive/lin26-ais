"""One-scenario, climate-coupled AISGBM projection for FACTS2.

Workflow: read annual FaIR members -> sample one configuration per member ->
evaluate mean/lower/upper GBM models -> draw emulator errors -> smooth and rebase
each trajectory -> write the requested years. All sea-level arrays are in metres
here, with shape (n_samples, 86) until the final selection of output years.

This workflow predicts forced runs directly. It does not subtract a control run
or add a background drift trend. Subtracting the sea-level value at baseyear
defines the output zero point and is separate from a physical drift correction.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from lin26_ais.io import (
    YEARS,
    normalize_scenario,
    output_years,
    read_fair_gsat,
    validate_input_files,
    write_outputs,
)
from lin26_ais.model import GradientBoostingModel


def _load_assets(paths: dict[str, Path]):
    """Load three fitted models, candidate configurations, and cached weights.

    Returns models in (mean, lower, upper) order, a DataFrame in the models'
    feature order, and one normalized sampling probability per DataFrame row.
    The historical calibration that produced the weights is not repeated here.
    """
    models = [
        GradientBoostingModel.load(paths[key])
        for key in ("mean_model", "lower_model", "upper_model")
    ]
    features = list(models[0].feature_names_in_)
    # All three models must see the same features in exactly the same order.
    if any(list(model.feature_names_in_) != features for model in models[1:]):
        raise ValueError("AISGBM models do not share a feature order")
    samples = pd.read_csv(paths["posterior_samples"])
    if not set(features).issubset(samples.columns):
        raise ValueError("Posterior samples do not contain all model features")
    samples = samples.loc[:, features]
    # Table row i and weight i refer to the same physical configuration. Validate
    # both their alignment and the probability distribution before sampling.
    weights = np.load(paths["posterior_weights"], allow_pickle=False)
    if (
        weights.ndim != 1
        or len(samples) != len(weights)
        or not np.isfinite(weights).all()
        or (weights < 0).any()
        or not np.isclose(weights.sum(), 1)
    ):
        raise ValueError("Posterior weights are invalid")
    return models, samples, weights


def _predict_raw(temperature_c, features, models):
    """Predict annual forced-run means and emulator standard deviations in metres.

    temperature_c is (n_samples, 86); features contains one fixed configuration
    per sample. Only Year and Climate Scenario are replaced as time advances.
    The cached categorical features, including GCM, stay with the configuration.
    """
    mean_model, lower_model, upper_model = models
    mean = np.empty_like(temperature_c)
    std = np.empty_like(temperature_c)
    working = features.copy()
    for column, year in enumerate(YEARS):
        # Every row keeps its own climate trajectory and configuration across all
        # years; no independent annual resampling of climate members takes place.
        working["Year"] = int(year)
        working["Climate Scenario"] = temperature_c[:, column]
        mean[:, column] = mean_model.predict(working)
        upper_prediction = upper_model.predict(working)
        lower_prediction = lower_model.predict(working)
        # Treat the upper/lower separation as approximately four standard
        # deviations, then add a 0.001 m (1 mm) uncertainty floor. This is a
        # per-row emulator error scale, not an ensemble percentile interval.
        std[:, column] = np.abs(upper_prediction - lower_prediction) / 4 + 0.001
    if (
        not np.isfinite(mean).all()
        or not np.isfinite(std).all()
    ):
        raise ValueError("AISGBM returned non-finite predictions")
    return mean, std


def _finalize(raw_mean, raw_std, baseyear, rng):
    """Return one realized trajectory in metres.

    All returned arrays retain shape (n_samples, 86). Smoothing and subtraction
    of a baseline are linear operations, so the same transformation can be used
    for the sampled trajectory. The raw standard deviation is used only to
    generate the emulator-error realization and is not written to diagnostics.
    """
    # Filtering columns of an identity matrix constructs the 86 x 86 operator S:
    # S @ trajectory applies the 19-year, first-order Savitzky-Golay filter.
    # Subtracting S's first row makes each smoothed path relative to 2015.
    smooth = savgol_filter(np.eye(len(YEARS)), 19, 1, axis=0)
    transform = smooth - smooth[:1]
    # Rebase the entire linear operator to the requested sea-level baseline.
    # The temperature reference remains 2015 even when baseyear is different.
    transform -= transform[baseyear - 2015 : baseyear - 2015 + 1].copy()

    # Prior and posterior use independent annual Gaussian errors before
    # filtering. Smoothing and rebasing themselves introduce correlations.
    noise = rng.standard_normal(raw_mean.shape)
    # Draw one trajectory per climate/configuration pair, not 100 copies as in
    # notebook plotting. Row-vector trajectories require the operator transpose.
    realized = (raw_mean + noise * raw_std) @ transform.T
    # Enforce exact zeros at the baseline, avoiding floating-point residuals.
    realized[:, baseyear - 2015] = 0
    return realized


def project(
    *,
    scenario: str,
    climate_file: Path,
    assets: dict[str, Path],
    output_file: Path,
    diagnostics_file: Path,
    nsamps: int | None = None,
    baseyear: int = 2015,
    pyear_start: int = 2015,
    pyear_end: int = 2100,
    pyear_step: int = 1,
    scheme: str = "posterior",
    seed: int = 42,
) -> None:
    """Run a single SSP while preserving FaIR sample IDs and row order.

    nsamps is an optional count check, not a new ensemble size. Each input member
    is paired with one configuration sampled with replacement: uniformly for
    prior or by cached likelihood weights for posterior.
    Computation always covers 2015-2100 annually; pyear_* selects exported years.
    The main file contains random realizations. The diagnostics file records
    the sampled configuration attached to each climate member.
    """
    scenario = normalize_scenario(scenario)
    # Resolve paths before checking aliases so an output cannot overwrite either
    # another output or an input under a different relative-path spelling.
    input_files = [climate_file, *assets.values()]
    output_paths = {output_file.resolve(), diagnostics_file.resolve()}
    if len(output_paths) != 2 or output_paths.intersection(
        path.resolve() for path in input_files
    ):
        raise ValueError(
            "Output files must be distinct from each other and from every input file"
        )
    if scheme not in {"prior", "posterior"}:
        raise ValueError("scheme must be prior or posterior")
    # Validate run settings and the climate contract before loading large assets.
    years = output_years(pyear_start, pyear_end, pyear_step, baseyear)
    input_paths = {"climate_file": climate_file, **assets}
    validate_input_files(input_paths)
    temperature, sample_ids = read_fair_gsat(climate_file, expected_scenario=scenario)
    if nsamps is not None and (nsamps < 1 or nsamps != len(sample_ids)):
        raise ValueError(
            f"nsamps={nsamps} does not match {len(sample_ids)} FAIR samples"
        )
    models, samples, weights = _load_assets(assets)
    rng = np.random.default_rng(seed)
    # Draw both index arrays in a fixed order regardless of the selected scheme.
    # Keep this order to preserve the configuration and emulator-error draws.
    prior_indices = rng.choice(len(samples), len(sample_ids), replace=True)
    posterior_indices = rng.choice(
        len(samples), len(sample_ids), replace=True, p=weights
    )
    indices = prior_indices if scheme == "prior" else posterior_indices
    # Align configuration row k to climate member k, retaining original climate
    # IDs for export. The same configuration stays attached across all years.
    selected_features = samples.iloc[indices].reset_index(drop=True).copy()
    raw_mean, raw_std = _predict_raw(temperature, selected_features, models)
    realized = _finalize(raw_mean, raw_std, baseyear, rng)
    # Select output years only after full-record smoothing, so annual and sparse
    # exports use the same trajectories and the same baseline subtraction.
    year_indices = years - 2015
    # Record enough run metadata to interpret units, baselines, and random draws.
    attrs = {
        "source": "Lin et al. (2026) AISGBM climate-coupled emulator",
        "scenario": scenario,
        "baseyear": baseyear,
        "scheme": scheme,
        "seed": seed,
        "climate_source": str(climate_file),
        "temperature_reference": "Each FAIR sample relative to its own 2015 value",
        "configuration_sampling": "One posterior/prior configuration per climate member",
        "emulator_error": "One Gaussian realization per member, smoothed and rebased",
        "drift_correction": "none",
    }
    # io.write_outputs performs the final metres-to-millimetres conversion.
    write_outputs(
        output_file,
        diagnostics_file,
        sample_ids=sample_ids,
        years=years,
        realized_m=realized[:, year_indices],
        config_indices=indices,
        config_features=selected_features,
        attrs=attrs,
    )
