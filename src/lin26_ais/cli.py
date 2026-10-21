"""Command-line entry point for the lin26-ais FACTS2 module.

This file only translates command-line arguments into the projection API. The
scientific calculation lives in project.py and input/output validation in io.py.
"""

from __future__ import annotations

from pathlib import Path

import click

from lin26_ais.project import project

# Default asset mount inside the FACTS container. Every asset path can also be
# supplied explicitly, allowing the same entry point to run outside a container.
ASSET_ROOT = Path("/mnt/module_specific_in")


def _path(value: str) -> Path:
    """Accept either slash style for paths passed by FACTS Experiment Builder."""
    # FEB currently emits Windows-mounted container paths with backslashes.
    return Path(value.replace("\\", "/"))


@click.command(context_settings={"auto_envvar_prefix": "LIN26", "show_default": True})
@click.argument("command", type=click.Choice(["main"]), default="main", required=False)
@click.option(
    "--scenario", required=True, help="Emission scenario for AIS projections."
)
@click.option(
    "--climate-data-file",
    type=_path,
    metavar="PATH",
    required=True,
    help="NetCDF file containing FaIR GSAT members for one scenario.",
)
@click.option(
    "--nsamps",
    type=int,
    help="Expected climate member count; validates the input without resampling.",
)
@click.option("--baseyear", type=int, default=2015, help="Sea-level baseline year.")
@click.option("--pyear-start", type=int, default=2015, help="First output year.")
@click.option("--pyear-end", type=int, default=2100, help="Last output year.")
@click.option("--pyear-step", type=int, default=1, help="Output year interval.")
@click.option(
    "--scheme",
    type=click.Choice(["prior", "posterior", "high_end"]),
    default="posterior",
    help="Configuration sampling and emulator error scheme.",
)
@click.option("--seed", type=int, default=42, help="Random number generator seed.")
@click.option(
    "--high-end-reference-file",
    type=_path,
    metavar="PATH",
    help="Separate SSP585 GSAT file required by the high_end scheme.",
)
@click.option(
    "--mean-model-file",
    type=_path,
    metavar="PATH",
    default=str(ASSET_ROOT / "models/mean_model.pkl"),
    help="Pre-trained mean model pickle file.",
)
@click.option(
    "--lower-model-file",
    type=_path,
    metavar="PATH",
    default=str(ASSET_ROOT / "models/lower_model.pkl"),
    help="Pre-trained lower model pickle file.",
)
@click.option(
    "--upper-model-file",
    type=_path,
    metavar="PATH",
    default=str(ASSET_ROOT / "models/upper_model.pkl"),
    help="Pre-trained upper model pickle file.",
)
@click.option(
    "--posterior-samples-file",
    type=_path,
    metavar="PATH",
    default=str(ASSET_ROOT / "posterior/posterior_samples.csv"),
    help="CSV table of candidate model configurations.",
)
@click.option(
    "--posterior-weights-file",
    type=_path,
    metavar="PATH",
    default=str(ASSET_ROOT / "posterior/posterior_weights.npy"),
    help="NumPy file of posterior sampling weights.",
)
@click.option(
    "--output-ais-gslr-file",
    type=_path,
    metavar="PATH",
    default="ais-gslr.nc",
    help="Output NetCDF file for AIS global sea-level projections.",
)
@click.option(
    "--output-diagnostics-file",
    type=_path,
    metavar="PATH",
    default="lin26-diagnostics.nc",
    help="Output NetCDF file for model diagnostics.",
)
def main(
    command: str,
    scenario: str,
    climate_data_file: Path,
    nsamps: int | None,
    baseyear: int,
    pyear_start: int,
    pyear_end: int,
    pyear_step: int,
    scheme: str,
    seed: int,
    high_end_reference_file: Path | None,
    mean_model_file: Path,
    lower_model_file: Path,
    upper_model_file: Path,
    posterior_samples_file: Path,
    posterior_weights_file: Path,
    output_ais_gslr_file: Path,
    output_diagnostics_file: Path,
) -> None:
    """Run the Lin et al. (2026) AIS projection workflow.

    The optional COMMAND accepts "main" for existing FACTS invocations.
    Options also accept LIN26_ environment variables, for example
    LIN26_SCENARIO and LIN26_CLIMATE_DATA_FILE.
    """
    # Pass named arguments through without changing sample order or units here.
    project(
        scenario=scenario,
        climate_file=climate_data_file,
        assets={
            "mean_model": mean_model_file,
            "lower_model": lower_model_file,
            "upper_model": upper_model_file,
            "posterior_samples": posterior_samples_file,
            "posterior_weights": posterior_weights_file,
        },
        output_file=output_ais_gslr_file,
        diagnostics_file=output_diagnostics_file,
        nsamps=nsamps,
        baseyear=baseyear,
        pyear_start=pyear_start,
        pyear_end=pyear_end,
        pyear_step=pyear_step,
        scheme=scheme,
        seed=seed,
        high_end_reference_file=high_end_reference_file,
    )


if __name__ == "__main__":
    main()
