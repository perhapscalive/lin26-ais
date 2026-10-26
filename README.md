# lin26-ais

An application producing Antarctic ice sheet (AIS) contributions to global mean
sea-level change using the emulator developed by Lin et al.
(2026). This module pairs each FaIR temperature member with a sampled ice-sheet
model configuration and writes projections in the FACTS2 NetCDF format.

## Example

This application runs on global surface air temperature (GSAT) projections from
the [FaIR temperature module](https://github.com/fact-sealevel/fair-temperature).
Use a scenario-specific `gsat.nc` file containing annual temperatures for
2015–2100, together with the pretrained emulator models and posterior assets.

### Setup

Clone the repository and download the [input data from Zenodo](https://doi.org/10.5281/zenodo.23668489).
The archive includes the pretrained emulator and posterior assets, FaIR GSAT
projections for all five supported scenarios, the inputs used to generate those
projections, and reproduction instructions. From the repository root, download
and extract it before running the module:

```bash
git clone https://github.com/perhapscalive/lin26-ais.git
cd lin26-ais
mkdir -p outputs/downloads
curl -fL --retry 3 \
  https://zenodo.org/api/records/23668489/files/lin26-ais-inputs.tgz/content \
  -o outputs/downloads/lin26-ais-inputs.tgz
tar -xzf outputs/downloads/lin26-ais-inputs.tgz
mkdir -p outputs/docker_tests/ssp245_posterior
```

Extracting the archive places the model and posterior assets in `data/`, and
the FaIR temperature output in `fair_temperature_runs/output/`, using the
following layout:

```text
data/
├── models/
│   ├── mean_model.pkl
│   ├── lower_model.pkl
│   └── upper_model.pkl
└── posterior/
    ├── posterior_samples.csv
    └── posterior_weights.npy
fair_temperature_runs/
└── output/
    └── ssp245/
        └── gsat.nc
```

These inputs are external assets and are not included in the Git repository or
Docker image. Keep the archive's directory structure when extracting it: the
example commands below use these paths directly. See
`fair_temperature_runs/REPRODUCE.md` in the archive to regenerate the GSAT
files with the FaIR temperature module.

The example commands use Bash on Linux or WSL Ubuntu and the published
`linux/amd64` image. On WSL, start Docker Desktop on Windows and enable your
Ubuntu distribution under **Settings > Resources > WSL Integration**. Check
that `docker version` shows both Client and Server. If access to
`/var/run/docker.sock` is denied, check `getent group docker`: if your username
is listed, run `newgrp docker`; otherwise run
`sudo usermod -aG docker "$USER"` and reopen your WSL session.

### Run the container

Download the first release:

```bash
docker pull ghcr.io/perhapscalive/lin26-ais:0.1.0
```

Run the SSP245 posterior projection, passing the input and output paths to the
command-line application:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$PWD/data,target=/mnt/module_specific_in,readonly" \
  --mount "type=bind,source=$PWD/fair_temperature_runs/output,target=/mnt/climate,readonly" \
  --mount "type=bind,source=$PWD/outputs/docker_tests/ssp245_posterior,target=/mnt/output" \
  ghcr.io/perhapscalive/lin26-ais:0.1.0 main \
  --scenario ssp245 \
  --climate-data-file /mnt/climate/ssp245/gsat.nc \
  --scheme posterior \
  --seed 42 \
  --baseyear 2015 \
  --pyear-start 2015 --pyear-end 2100 --pyear-step 1 \
  --output-ais-gslr-file /mnt/output/ais-gslr.nc \
  --output-diagnostics-file /mnt/output/ais-diagnostics.nc
```

The model and posterior paths default to `/mnt/module_specific_in`, matching the
first mount. Inputs are mounted read-only. Create the host output directory
before running the container; `--user` gives the generated files your WSL/Linux
UID and GID. Successful runs write two NetCDF files to
`outputs/docker_tests/ssp245_posterior/`.

## Features

### Projection schemes

| Scheme | Configuration sampling and emulator errors |
| --- | --- |
| `prior` | Sample configurations uniformly, with independent annual Gaussian emulator errors before smoothing. |
| `posterior` | Sample configurations using the cached posterior weights, with independent annual Gaussian emulator errors before smoothing. This is the default. |
| `high_end` | Screen posterior-weighted candidates using SSP585 warming in 2100, retain the highest 1% of predicted contributions, and use emulator errors with a five-year exponential correlation timescale. |

For `high_end`, also place the SSP585 `gsat.nc` under
`fair_temperature_runs/output/ssp585/`, set `--scheme high_end`, and add:

```text
--high-end-reference-file /mnt/climate/ssp585/gsat.nc
```

The SSP585 file is used to select configurations; the projection still follows
the temperature members in `--climate-data-file`. The reference-file option is
valid only for `high_end`. Use a separate output directory for each scenario
and scheme.

### Climate input and sample coupling

- Supported scenarios are `ssp119`, `ssp126`, `ssp245`, `ssp370`, and `ssp585`.
- The input NetCDF must declare the matching `Scenario` or `scenario` attribute
  and contain `surface_temperature` with `samples`, `years`, and `locations`
  dimensions. The only location must be the global identifier `-1`.
- Temperatures must be finite and in degrees Celsius (`degC`, `C`,
  `degree_Celsius`, or `degrees_Celsius`). All annual years from 2015 through
  2100 are required; additional years are allowed.
- Sample IDs must be unique integers. Their identity and order are preserved;
  each climate member is paired with one sampled model configuration.
  `--nsamps` optionally checks the member count and does not resample or resize
  the climate ensemble.
- Temperatures are referenced to each member's own 2015 value. Sea-level
  trajectories are smoothed and rebased to `--baseyear` before selecting output
  years. The calculation uses forced runs without a control-run subtraction or
  background drift correction.

### Command-line options

The application accepts `lin26-ais [OPTIONS] [main]`. The optional `main`
argument supports existing FACTS invocations.

| Option | Description | Default |
| --- | --- | --- |
| `--scenario` | Emission scenario matching the climate file. | Required |
| `--climate-data-file` | FaIR GSAT NetCDF for one scenario. | Required |
| `--scheme` | `prior`, `posterior`, or `high_end`. | `posterior` |
| `--seed` | Random seed for configuration sampling and emulator errors. | `42` |
| `--nsamps` | Expected number of climate members; validates without resampling. | Inferred from input |
| `--baseyear` | Sea-level baseline year, within 2015–2100. | `2015` |
| `--pyear-start` | First output year. | `2015` |
| `--pyear-end` | Last output year. | `2100` |
| `--pyear-step` | Output interval in years. | `1` |
| `--high-end-reference-file` | Separate SSP585 GSAT input, required for `high_end`. | None |
| `--mean-model-file` | Pretrained mean model pickle. | `/mnt/module_specific_in/models/mean_model.pkl` |
| `--lower-model-file` | Pretrained lower model pickle. | `/mnt/module_specific_in/models/lower_model.pkl` |
| `--upper-model-file` | Pretrained upper model pickle. | `/mnt/module_specific_in/models/upper_model.pkl` |
| `--posterior-samples-file` | Candidate configuration CSV containing all model features. | `/mnt/module_specific_in/posterior/posterior_samples.csv` |
| `--posterior-weights-file` | Normalized posterior weights, one per configuration. | `/mnt/module_specific_in/posterior/posterior_weights.npy` |
| `--output-ais-gslr-file` | AIS global sea-level projection NetCDF. | `ais-gslr.nc` |
| `--output-diagnostics-file` | Model diagnostics NetCDF. | `ais-diagnostics.nc` |

Output years must form an evenly spaced range within 2015–2100 and include at
least two years. The baseline year may fall outside the selected output grid.
Options also accept `LIN26_` environment variables, such as `LIN26_SCENARIO`.

See the complete help by passing `--help`:

```bash
docker run --rm ghcr.io/perhapscalive/lin26-ais:0.1.0 --help
```

## Building the container locally

From the repository root, build the image and check the command-line interface:

```bash
docker build --platform linux/amd64 -t lin26-ais:0.1.0 .
docker run --rm lin26-ais:0.1.0 --help
```

Use `lin26-ais:0.1.0` in place of the GHCR image name in the example above to run
your local build. The image includes Python 3.13 and the locked application
dependencies, runs as non-root by default, and uses external data mounts.

For local Python development, install [uv](https://docs.astral.sh/uv/), then run:

```bash
uv sync --locked
uv run --locked lin26-ais main \
  --scenario ssp245 \
  --climate-data-file fair_temperature_runs/output/ssp245/gsat.nc \
  --scheme posterior \
  --seed 42 \
  --mean-model-file data/models/mean_model.pkl \
  --lower-model-file data/models/lower_model.pkl \
  --upper-model-file data/models/upper_model.pkl \
  --posterior-samples-file data/posterior/posterior_samples.csv \
  --posterior-weights-file data/posterior/posterior_weights.npy \
  --output-ais-gslr-file outputs/quick_tests/ssp245_posterior/ais-gslr.nc \
  --output-diagnostics-file outputs/quick_tests/ssp245_posterior/ais-diagnostics.nc
```

This command uses the same host input layout and writes to
`outputs/quick_tests/ssp245_posterior/`.

The [Container workflow](.github/workflows/container.yaml) builds and checks
pull requests and pushes to `main`. Matching release tags, such as `v0.1.0` for
project version `0.1.0`, also publish versioned images to
`ghcr.io/perhapscalive/lin26-ais`; stable releases update `latest`. The published
`0.1.0` image is available without registry login. Pin the version tag when
running a specific release.

## Results

Successful runs produce two NetCDF files at the requested output paths:

| File | Contents |
| --- | --- |
| `ais-gslr.nc` | `sea_level_change(samples, years, locations)`: one realized AIS contribution per climate member, in millimetres relative to `baseyear`. The global location is `-1`. |
| `ais-diagnostics.nc` | Conditional means, emulator standard deviations, input temperatures, source sample IDs, and sampled configuration indices and parameters. |

The diagnostic variables `predicted_mean` and `emulator_standard_deviation` use
millimetres; `input_temperature` uses degrees Celsius relative to 2015. The
standard deviation describes emulator uncertainty conditional on a member and
its configuration, rather than the spread across the ensemble. Configuration
indices can repeat because sampling uses replacement.

With the example settings, both files contain 86 annual output years from 2015
to 2100 and preserve the climate input's sample IDs and ordering. Sea-level
values at the baseline year are zero when that year is included in the output.
This module produces the total AIS contribution to global mean sea level;
regional localization is a separate processing step.

## Support

Source code: https://github.com/perhapscalive/lin26-ais

Please report issues at https://github.com/perhapscalive/lin26-ais/issues.
