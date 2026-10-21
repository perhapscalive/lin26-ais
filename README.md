# lin26-ais
This FACTS2 module projects Antarctic ice sheet contributions to global mean sea
level using the Lin et al. (2026) climate-coupled emulator.

## Run with Docker

The image contains the application and its locked dependencies on Python 3.13.
Model assets, climate inputs, and generated outputs are supplied through bind
mounts; they are not included in the image. Run the following commands in Bash
from the repository root.

### Docker Desktop with WSL Ubuntu

Start Docker Desktop on Windows, use Linux containers, and enable your Ubuntu
distribution in **Settings > Resources > WSL Integration**. Check the connection
from your WSL terminal:

```bash
docker version
```

Both Client and Server should be shown. If access to `/var/run/docker.sock` is
denied and `getent group docker` already lists your username, run
`newgrp docker` to activate that membership in a new shell, then retry. If your
user is not a member, run `sudo usermod -aG docker "$USER"` first and reopen your
WSL session. There is no need to install a separate Docker Engine in Ubuntu.

### Build and check the image

```bash
docker build --platform linux/amd64 -t lin26-ais:0.1.0 .
docker run --rm lin26-ais:0.1.0 --help
```

This builds a local image for an x86-64 PC. The image's entry point is
`lin26-ais`, so pass application arguments directly after the image tag.

### Run a projection

Prepare these existing inputs on the host:

```text
data/
  models/{mean,lower,upper}_model.pkl
  posterior/posterior_samples.csv
  posterior/posterior_weights.npy
fair_temperature_runs/output/ssp245/gsat.nc
```

Run the default SSP245/posterior projection:

```bash
mkdir -p outputs/docker_tests/ssp245_posterior

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$PWD/data,target=/mnt/module_specific_in,readonly" \
  --mount "type=bind,source=$PWD/fair_temperature_runs/output,target=/mnt/climate,readonly" \
  --mount "type=bind,source=$PWD/outputs/docker_tests/ssp245_posterior,target=/mnt/output" \
  lin26-ais:0.1.0 main \
  --scenario ssp245 \
  --climate-data-file /mnt/climate/ssp245/gsat.nc \
  --scheme posterior \
  --seed 42 \
  --output-ais-gslr-file /mnt/output/ais-gslr.nc \
  --output-diagnostics-file /mnt/output/lin26-diagnostics.nc
```

The application uses its default model paths under `/mnt/module_specific_in`.
Inputs are mounted read-only. The output mount is writable, and `--user` writes
files with your WSL UID/GID instead of the image's default non-root UID/GID
`9876:9876`. Create the host output directory before running the container.

Results appear in `outputs/docker_tests/ssp245_posterior/`: `ais-gslr.nc` contains
sea-level realizations in millimetres, and `lin26-diagnostics.nc` contains model
diagnostics. The default output years are 2015–2100, relative to 2015. Each input
climate member is retained; `--nsamps` is an optional count check, not a way to
resize the ensemble.

For the prior scheme, set `--scheme prior`. For the high-end scheme, set
`--scheme high_end` and add
`--high-end-reference-file /mnt/climate/ssp585/gsat.nc`; that SSP585 input must
also exist in the mounted climate directory. Use a separate host output
directory for each run. Missing input directories or files are checked by the
Python application before data or models are loaded.

The existing model pickles were trained with scikit-learn 1.4.0. The project pins
1.5.2, which loads these assets on Python 3.13; model loading still reports an
`InconsistentVersionWarning`. Newer scikit-learn versions fail to load these
pickles. The local/container smoke checks verify execution and output agreement,
not compatibility with every estimator version.

### Automatic builds and publishing to GHCR

The [Container workflow](.github/workflows/container.yaml) builds and checks the
image for pull requests and pushes to `main`. You can also run those checks with
**Actions > Container > Run workflow**. These runs do not publish an image.

Pushing a version tag such as `v0.1.0` builds, checks, and publishes the image to
GitHub Container Registry (GHCR). The tag must match the version declared in
`pyproject.toml`; a mismatch fails before the build. Stable releases receive both
a version tag and `latest`:

```text
ghcr.io/perhapscalive/lin26-ais:0.1.0
ghcr.io/perhapscalive/lin26-ais:latest
```

The workflow builds `linux/amd64` images and tests CLI startup, the installed
package version, the scikit-learn dependency, and the non-root runtime user
before publishing. Full scientific runs require the external model and climate
assets and are verified locally with the mounts above.

To publish the first release, commit the Docker configuration and workflow,
push the commit to `main`, and push its version tag:

```bash
git push origin main
git tag -a v0.1.0 -m "Release lin26-ais 0.1.0"
git push origin v0.1.0
```

The workflow uses GitHub's automatic `GITHUB_TOKEN` with `contents: read` and
`packages: write`; no personal access token or extra repository secret is
needed. Actions must be enabled in the repository. If an organization policy
blocks package writes or third-party actions, its owner must allow them.

Follow the run at
[GitHub Actions](https://github.com/perhapscalive/lin26-ais/actions/workflows/container.yaml).
After the first successful publication, open the package from the repository's
**Packages** section and check **Package settings > Change visibility**. New
packages can be private even when the source repository is public; set this
package to **Public** to allow anonymous FACTS2 downloads. The workflow's OCI
source label links the package to this repository.

Users can then download and check the image without building it:

```bash
docker pull ghcr.io/perhapscalive/lin26-ais:0.1.0
docker run --rm ghcr.io/perhapscalive/lin26-ais:0.1.0 --help
```

Use that registry image name in place of `lin26-ais:0.1.0` in the projection
command above; the same inputs and output mounts are required.

The remaining sections describe the FACTS2 module template and development
requirements.

## Requirements of a FACTS2 module
This section describes attributes of a module in the FACTS2 ecosystem. 

### 1. Module has an associated GitHub repository
This is the repository that you create based off of this template. It can be located in the [fact-sealevel](https://github.com/fact-sealevel) GitHub organization or elsewhere. If it is located elsewhere, the repository must be public and must have permissions for GitHub Packages. You can read more about these [here](https://docs.github.com/en/packages/learn-github-packages/introduction-to-github-packages). If you're unsure about any of this, please reach out to us! We are happy to help sort through this part of module development. 

### 2. The module is a command line application
All modules in the FACTS2 ecosystem must be command line applications. We provide instructions that use the [Click](https://click.palletsprojects.com/en/stable/) (Command Line Interface Creation Kit) package but you are also free to use another method if you prefer. 

If you'd like guidance on structuring your module as a command line application, check out our [module development tutorial]() (coming soon). Our instructions use [uv](https://docs.astral.sh/uv/) for package management, but you can use whatever works for you. 

### 3. The module application has a Docker image
All FACTS2 modules must contain a [Dockerfile](https://docs.docker.com/build/concepts/dockerfile/) in order to build an image of the Docker container associated with the module. We recommend using GitHub Actions to build and deploy an image that is hosted in a Docker Container Registry. 

### 4. Module input data is archived and publicly available

We’re happy to create and submit a Zenodo record for your module input data in the fact-sealevel Zenodo community. If you’d rather archive the data yourself or use something other than Zenodo, that is also fine as long as it has a publicly accessible DOI.

Accompanying module input data, there must be instructions to generate that input data. We recommend using this template, but exact guidance is still being developed.

### 5. Module has an entry in the facts module registry

The [FACTS module registry](https://github.com/fact-sealevel/facts-module-registry) is the interface through which the FACTS Experiment Builder (FEB) engages with modules in the FACTS2 ecosystem. Our module development tutorial (coming soon) will demonstrate creating an entry in the module registry. 

### 6. The module accepts standard forcing inputs and produces standard outputs

Check back for more information on this soon. 

## Contents
This section describes each of the other files you'll see in this repository. 

### [Changelog](CHANGELOG.md)
**Nice to have**. 
This is used to track changes in the module. We use the [keep a changelog](https://keepachangelog.com/en/1.1.0/) framework. 

### [.dockerignore](.dockerignore) and [.gitignore](.gitignore)
**Need to have**
These ensure certain files are not tracked by GitHub and when creating a Docker container. The versions provided in this repository are a pretty good start but you can make any modifications or additions that are necessary. 

### [LICENSE](LICENSE)
**Need to have**
We recomend the MIT license. 

### [justfile](justfile)
**Nice to have**
This helps with formatting and automatically running checks and tests in your repostiory. You can read more about it [here](https://just.systems/man/en/). 

### GitHub workflows files
**Need to have**
The active [container.yaml](./.github/workflows/container.yaml) builds and checks
the Docker image and publishes version tags to GHCR, as described above.
[pythonpackage.yaml](./.github/inactive-workflows/pythonpackage.yaml) remains an
inactive template for Python formatting and lint checks.

### .python-version, uv.lock and pyproject.toml

These files are created by running the following uv `init` command. From the root of the module repository, run: 
```shell
uv init --app --package 
```
The [pyproject.toml](pyproject.toml) is a configuration file for your Python project (the FACTS module). Dependencies are listed under the [project] table (See line 10). In the example provided here, we have only added one dependency, the click package. Dependencies are added by running the following:
```
uv add <package name>
```
To add the dependency to the project. And
```
uv sync
```
To update the project's environment to include the new dependency. 

As you build your module, run `uv add ...` to add any required packages such as Xarray, SciPy, etc. 

The [uv.lock](uv.lock) is a cross-platform lockfile that contains the exact resolved versions of all packages installed in the project environment. You can read more about it [here](https://docs.astral.sh/uv/concepts/projects/layout/#the-lockfile). When you add a dependency to your project, both the pyproject.toml and uv.lock files are updated. 

The [.python-version](.python-version) file specifies the Python version used in the project. Read more [here](https://docs.astral.sh/uv/concepts/python-versions/#python-version-files).

The `uv init` command also created a directory, `./src/`, containing a `__init__.py` file. This will hold the scripts in your package. (To do: add / ref IO fns provided by FACTS). For an example of how to create the rest of the scripts in the module see our [module development tutorial]() (coming soon).
