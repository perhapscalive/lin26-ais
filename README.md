# module-template
This repository is a starting point for a FACTS2 module. It has everything necessary to run a module in the FACTS2 framework *except* the actual science, which will be added by the module developer. If you are developing a FACTS2 module in Python, we recommend creating a repository for your module based off of this template. 

This README contains an overview of the different components of this repository as well as instructions for adding and generating elements that will be specific to your module. 

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
NOTE: Currently, these files are in `./.github/inactive-workflows` instead of `./.github/workflows`. When you are ready to run these commands (your module is nearly complete), move them into the `workflows/` directory and they will be picked up in CI/CD.

These are [container.yaml](./.github/inactive-workflows/container.yaml) and [pythonpackage.yaml](./.github/inactive-workflows/pythonpackage.yaml). These trigger certain actions when you push changes in your repository to GitHub. The pythonpackage file runs linting and formatting checks. The container file uses the Dockerfile in the repository and creates a Docker Image that is stores it in the GitHub container [registry](https://github.com/orgs/fact-sealevel/packages) assocaited with the fact-sealevel org (or another location). 

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
