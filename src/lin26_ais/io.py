"""Read FaIR temperature members and write FACTS sea-level products.

Climate files represent one SSP, with samples, years, and one global location.
Arrays returned to the emulator have shape (n_samples, 86). Temperature is in
degrees Celsius relative to each member's 2015 value. Sea level is calculated in
metres by project.py and converted to millimetres only when written here.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import xarray as xr

# The fitted emulator and smoothing workflow use all 86 annual time points.
YEARS = np.arange(2015, 2101, dtype=np.int64)
SCENARIOS = frozenset({"ssp119", "ssp126", "ssp245", "ssp370", "ssp585"})


def validate_input_files(paths: dict[str, Path]) -> None:
    """Check input directories and files before opening any projection inputs."""
    errors = []
    for name, path in paths.items():
        if not path.parent.is_dir():
            errors.append(
                f"{name}: input directory does not exist or is not a directory: {path.parent}"
            )
        elif not path.is_file():
            errors.append(
                f"{name}: input file does not exist or is not a regular file: {path}"
            )
    if errors:
        raise FileNotFoundError("Invalid projection inputs:\n" + "\n".join(errors))


def normalize_scenario(value: str) -> str:
    """Normalize labels such as 'SSP2-4.5' to the supported key 'ssp245'."""
    scenario = re.sub(r"[^a-z0-9]", "", str(value).lower())
    if scenario not in SCENARIOS:
        raise ValueError(
            f"Unsupported scenario {value!r}; expected one of {sorted(SCENARIOS)}"
        )
    return scenario


def read_fair_gsat(
    path: Path, *, expected_scenario: str
) -> tuple[np.ndarray, np.ndarray]:
    """Return (warming_c, sample_ids), retaining the climate file's member order.

    warming_c has shape (n_samples, 86), ordered from 2015 through 2100; sample_ids
    has shape (n_samples,). Requiring the full annual record lets downstream
    smoothing use the same time grid regardless of the requested output years.
    """
    expected_scenario = normalize_scenario(expected_scenario)
    with xr.open_dataset(path) as dataset:
        # Check the declared scenario rather than inferring it from the filename.
        source_scenario = dataset.attrs.get("Scenario", dataset.attrs.get("scenario"))
        if (
            source_scenario is None
            or normalize_scenario(source_scenario) != expected_scenario
        ):
            raise ValueError(
                f"{path} scenario {source_scenario!r} does not match {expected_scenario!r}"
            )
        if "surface_temperature" not in dataset:
            raise ValueError(f"{path} has no surface_temperature variable")
        temperature = dataset["surface_temperature"]
        # Dimension order may vary on disk; reorder explicitly after validation.
        if set(temperature.dims) != {"samples", "years", "locations"}:
            raise ValueError(
                f"{path} surface_temperature must have samples, years, locations dimensions"
            )
        # FACTS uses location -1 for a global value. Regional temperatures cannot
        # be passed directly to this global-mean-temperature emulator.
        if dataset.sizes["locations"] != 1 or dataset["locations"].values.tolist() != [
            -1
        ]:
            raise ValueError(f"{path} must contain the global location -1 only")
        sample_ids = np.asarray(dataset["samples"].values)
        # Preserve member identity for coupling to other FACTS components. IDs
        # need not be consecutive or sorted, but each must identify one member.
        if (
            sample_ids.ndim != 1
            or sample_ids.size == 0
            or not np.issubdtype(sample_ids.dtype, np.integer)
            or np.unique(sample_ids).size != sample_ids.size
        ):
            raise ValueError(f"{path} must have unique integer sample IDs")
        available_years = np.asarray(dataset["years"].values)
        # Extra years are allowed; missing or duplicate annual years are not.
        if (
            not np.issubdtype(available_years.dtype, np.integer)
            or np.unique(available_years).size != available_years.size
            or not np.isin(YEARS, available_years).all()
        ):
            raise ValueError(
                f"{path} must contain unique years including 2015 through 2100"
            )
        units = temperature.attrs.get("units")
        # Reject other units instead of silently treating Kelvin as Celsius.
        if units not in {"degC", "C", "degree_Celsius", "degrees_Celsius"}:
            raise ValueError(
                f"{path} temperature units must be degrees Celsius, got {units!r}"
            )
        # Selecting the scalar location removes that axis. Load the numerical
        # array while the file is open, in the fixed (samples, years) order.
        values = (
            temperature.sel(locations=-1, years=YEARS)
            .transpose("samples", "years")
            .to_numpy()
            .astype(np.float64)
        )
    if not np.isfinite(values).all():
        raise ValueError(f"{path} contains non-finite temperature values")
    # (n_samples, 1) broadcasts along years: subtract each member's own 2015
    # temperature. An input already relative to 2015 is unchanged by this step.
    return values - values[:, :1], sample_ids.astype(np.int64)


def output_years(start: int, end: int, step: int, baseyear: int) -> np.ndarray:
    """Validate the sea-level baseline and return an inclusive output-year grid.

    baseyear need not appear in the output grid: baseline subtraction is performed
    on the full annual record before the requested output years are selected.
    """
    if not 2015 <= baseyear <= 2100:
        raise ValueError("baseyear must be between 2015 and 2100")
    if step < 1 or not 2015 <= start < end <= 2100 or (end - start) % step:
        raise ValueError(
            "Projection years must be an evenly spaced range within 2015-2100"
        )
    years = np.arange(start, end + 1, step, dtype=np.int64)
    if years.size < 2:
        raise ValueError("Projection output requires at least two years")
    return years


def _base_dataset(sample_ids: np.ndarray, years: np.ndarray, attrs: dict) -> xr.Dataset:
    """Create coordinates and global-location placeholders shared by both files."""
    # Latitude/longitude infinity values are placeholders for a global quantity,
    # not actual geographic coordinates; the global location identifier is -1.
    return xr.Dataset(
        data_vars={
            "lat": (("locations",), np.array([np.inf], dtype=np.float32)),
            "lon": (("locations",), np.array([np.inf], dtype=np.float32)),
        },
        coords={
            "samples": sample_ids,
            "years": years,
            "locations": np.array([-1], dtype=np.int64),
        },
        attrs=attrs,
    )


def write_outputs(
    output_file: Path,
    diagnostics_file: Path,
    *,
    sample_ids: np.ndarray,
    years: np.ndarray,
    realized_m: np.ndarray,
    mean_m: np.ndarray,
    std_m: np.ndarray,
    temperature_c: np.ndarray,
    config_indices: np.ndarray,
    config_features,
    attrs: dict,
) -> None:
    """Write the realized AIS contribution and a separate diagnostic dataset.

    realized_m, mean_m, std_m, and temperature_c have shape (n_samples, n_years).
    Each row pairs one original FaIR member with one sampled configuration.
    std_m describes emulator uncertainty conditional on that pair; it is not
    the spread or 5th-95th percentile range across ensemble members.
    """
    for path in (output_file, diagnostics_file):
        path.parent.mkdir(parents=True, exist_ok=True)
    main = _base_dataset(sample_ids, years, attrs)
    # Add a singleton global-location axis to satisfy the FACTS output contract:
    # (samples, years) -> (samples, years, locations). Convert metres to mm.
    main["sea_level_change"] = (
        ("samples", "years", "locations"),
        (realized_m[:, :, None] * 1000).astype(np.float32),
        {
            "units": "mm",
            "long_name": "Antarctic ice sheet contribution to global mean sea level",
        },
    )
    main.to_netcdf(
        output_file,
        engine="netcdf4",
        encoding={"sea_level_change": {"zlib": True, "complevel": 4, "dtype": "f4"}},
    )

    # Diagnostics keep the conditional mean and standard deviation apart from
    # the single random realization supplied to the FACTS sea-level ensemble.
    diagnostics = _base_dataset(sample_ids, years, attrs)
    for name, values, units in (
        ("predicted_mean", mean_m * 1000, "mm"),
        ("emulator_standard_deviation", std_m * 1000, "mm"),
        ("input_temperature", temperature_c, "degC relative to 2015"),
    ):
        diagnostics[name] = (
            ("samples", "years"),
            values.astype(np.float32),
            {"units": units},
        )
    diagnostics["source_sample_id"] = (("samples",), sample_ids)
    # Row number in the cached configuration table; repeated indices are valid
    # because configurations are sampled with replacement.
    diagnostics["model_config_index"] = (("samples",), config_indices.astype(np.int64))
    for column in config_features.columns:
        # Year and warming vary over time and are not fixed configuration values.
        if column in {"Year", "Climate Scenario"}:
            continue
        # Convert feature labels to stable NetCDF names and retain the original
        # label as metadata. Reject collisions introduced by this normalization.
        name = "parameter_" + re.sub(r"[^a-z0-9]+", "_", column.lower()).strip("_")
        if name in diagnostics:
            raise ValueError(f"Duplicate diagnostic feature name {name}")
        diagnostics[name] = (
            ("samples",),
            config_features[column].to_numpy(),
            {"source_feature": column},
        )
    diagnostics.to_netcdf(diagnostics_file, engine="netcdf4")
