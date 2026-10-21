"""Command-line entry point for the lin26-ais FACTS2 module.

This file only translates command-line arguments into the projection API. The
scientific calculation lives in project.py and input/output validation in io.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lin26_ais.project import project


# Default asset mount inside the FACTS container. Every asset path can also be
# supplied explicitly, allowing the same entry point to run outside a container.
ASSET_ROOT = Path("/mnt/module_specific_in")


def _path(value: str) -> Path:
    """Accept either slash style for paths passed by FACTS Experiment Builder."""
    # FEB currently emits Windows-mounted container paths with backslashes.
    return Path(value.replace("\\", "/"))


def main() -> None:
    """Parse one scenario's run options and write projection and diagnostic files."""
    parser = argparse.ArgumentParser(description=__doc__)
    # FACTS invokes the module with the positional subcommand "main".
    parser.add_argument("command", choices=["main"])
    # The climate file contains all members of a single SSP. nsamps, when given,
    # checks its member count; it does not request resampling of climate members.
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--climate-data-file", type=_path, required=True)
    parser.add_argument("--nsamps", type=int)
    # Output may cover a subset of years, but the emulator always computes the
    # full annual 2015-2100 record before smoothing and baseline subtraction.
    parser.add_argument("--baseyear", type=int, default=2015)
    parser.add_argument("--pyear-start", type=int, default=2015)
    parser.add_argument("--pyear-end", type=int, default=2100)
    parser.add_argument("--pyear-step", type=int, default=1)
    # The scheme controls configuration sampling and, for high_end, temporal
    # correlation of emulator errors. seed makes these random choices repeatable.
    parser.add_argument("--scheme", choices=["prior", "posterior", "high_end"], default="posterior")
    parser.add_argument("--seed", type=int, default=42)
    # high_end alone requires a separate SSP585 climate file to screen candidate
    # configurations, even when the requested projection uses another scenario.
    parser.add_argument("--high-end-reference-file", type=_path)
    # Three fitted models define the central prediction and uncertainty width;
    # the candidate table and weights are precomputed assets, not fitted here.
    parser.add_argument("--mean-model-file", type=_path, default=ASSET_ROOT / "models/mean_model.pkl")
    parser.add_argument("--lower-model-file", type=_path, default=ASSET_ROOT / "models/lower_model.pkl")
    parser.add_argument("--upper-model-file", type=_path, default=ASSET_ROOT / "models/upper_model.pkl")
    parser.add_argument(
        "--posterior-samples-file", type=_path, default=ASSET_ROOT / "posterior/posterior_samples.csv"
    )
    parser.add_argument(
        "--posterior-weights-file", type=_path, default=ASSET_ROOT / "posterior/posterior_weights.npy"
    )
    # Keep the standard FACTS sea-level product separate from detailed model
    # diagnostics such as selected parameters and conditional standard deviations.
    parser.add_argument("--output-ais-gslr-file", type=_path, default=Path("ais-gslr.nc"))
    parser.add_argument(
        "--output-diagnostics-file", type=_path, default=Path("lin26-diagnostics.nc")
    )
    args = parser.parse_args()
    # Pass named arguments through without changing sample order or units here.
    project(
        scenario=args.scenario,
        climate_file=args.climate_data_file,
        assets={
            "mean_model": args.mean_model_file,
            "lower_model": args.lower_model_file,
            "upper_model": args.upper_model_file,
            "posterior_samples": args.posterior_samples_file,
            "posterior_weights": args.posterior_weights_file,
        },
        output_file=args.output_ais_gslr_file,
        diagnostics_file=args.output_diagnostics_file,
        nsamps=args.nsamps,
        baseyear=args.baseyear,
        pyear_start=args.pyear_start,
        pyear_end=args.pyear_end,
        pyear_step=args.pyear_step,
        scheme=args.scheme,
        seed=args.seed,
        high_end_reference_file=args.high_end_reference_file,
    )


if __name__ == "__main__":
    main()
