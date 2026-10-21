"""
Read and write projections generated within FACTS experiments.
 
This module holds the input/output helpers used at the different steps of a
FACTS experiment: the climate step, the global mean sea level (GMSL) step, and
the relative sea level (RSL) step. Each step has a paired reader and writer so
that on-disk conventions (NetCDF4 groups, variable names, compression settings)
live in one place.
 
Notes
-----
All writers serialise to NetCDF4. The climate-step writer additionally
validates the structure of the dataset and applies per-variable compression;
the GMSL and RSL writers pass the dataset through unmodified.
"""
import xarray as xr
from typing import Literal

## The following functions handle IO for projections generated at different steps of a FACTS experiment

# Read & write climate step projections
def write_climate_step_projections(
        projections: xr.Dataset,
        output_file: str,
        output_type: Literal["gsat","ohc","deep_ocean_temperature", "climate"]
):
    """This is a function provided to write outputs from a FACTS climate module to a NetCDF4 file.
    Provide the prepared xr.Datset object that holds the projections, 
    the output path where the file will be written, 
    and specify the type of output """
    # Check expected dimensions, coords and data variables
    assert set(projections.dims) == {"years","samples"}, (
        f"Expected dimensions 'years' and 'samples', got {set(projections.dims)}"
    )
    assert set(projections.coords) == {"years","samples"},(
        f"Expected coordinates 'years' and 'samples', got {set(projections.coords)}"
    )

    expected_vars = {
        "gsat": {"surface_temperature"},
        "ohc": {"ohc"},
        "deep_ocean_temperature":{"deep_ocean_temperature"},
        "climate":{"surface_temperature","ocean_heat_content","deep_ocean_temperature"},
    }
    if output_type not in expected_vars:
        raise ValueError(
            f"Invalid output_type '{output_type}', expected one of 'gsat','ohc','deep_ocean_temperature', or 'climate'"
        )
    assert set(projections.data_vars) == expected_vars[output_type], (
        f"Expected data variable(s) {expected_vars[output_type]}, got {set(projections.data_vars)}"
    )
    encoding_by_type = {
        "gsat":{"surface_temperature": {"dtype": "float32","zlimb": True, "complevel": 4}},
        "ohc":{"ohc": {"dtype":"float32","zlib":True,"complevel":4}},
        "deep_ocean_temperature":{
            "deep_ocean_temperature":{
            "dtype":"float32","zlib":True,"complevel":4}
            },
        "climate":{
            "surface_temperature":{"dtype":"float32","zlib":True, "complevel":4},
            "ocean_heat_content":{"dtype":"float32","zlib":True, "complevel":4},
            "deep_ocean_tempearture":{"dtype":"float32","zlib":True, "complevel":4}
        }
    },
    return projections.to_netcdf(
        output_file,
        encoding = encoding_by_type[output_type]
    )

def read_climate(path: str):
    """
    Read the output of the climate step into memory.
 
    Parameters
    ----------
    path : str
        Path to the climate data file written by the FACTS climate step.

    Returns
    -------
    xarray.Dataset
        Dataset holding the climate projections.
 
    See Also
    --------
    write_climate_step_projections : Write climate-step projections to disk.
 
    Notes
    -----
    The dataset is opened lazily, so variable values are read from disk only
    when they are accessed. The underlying file handle stays open until the
    dataset is closed.
 
    Examples
    --------
    >>> ds = read_climate("climate.nc")  # doctest: +SKIP
    """
    return xr.open_dataset(path)


# Read and write gmsl projections
def write_gmsl_projections(projections: xr.Dataset, output_file: str):
    """
    Write global mean sea level projections to a NetCDF file.
 
    Parameters
    ----------
    projections : xarray.Dataset
        Dataset holding the GMSL projections to serialise.
    output_file : str
        Path of the NetCDF file to write. An existing file is overwritten.
 
    Returns
    -------
    None
 
    See Also
    --------
    read_gmsl_projections : Read GMSL projections back into memory.
 
    Notes
    -----
    The dataset is written as-is: no validation is performed and no encoding
    or compression is applied.
    """
    projections.to_netcdf(output_file)

def read_gmsl_projections(path: str)-> xr.Dataset:
    """
    Read global mean sea level projections into memory.
 
    Parameters
    ----------
    path : str
        Path to the NetCDF file holding the GMSL projections.
 
    Returns
    -------
    xarray.Dataset
        Dataset holding the GMSL projections.
 
    See Also
    --------
    write_gmsl_projections : Write GMSL projections to disk.
 
    Notes
    -----
    The dataset is opened lazily, so variable values are read from disk only
    when they are accessed.
    """
    return xr.open_dataset(path)

# Read and write rsl projections
def write_rsl_projections(projections:xr.Dataset, output_file:str):
    """
    Write relative sea level projections to a NetCDF file.
 
    Parameters
    ----------
    projections : xarray.Dataset
        Dataset holding the RSL projections to serialise.
    output_file : str
        Path of the NetCDF file to write. An existing file is overwritten.
 
    Returns
    -------
    None

    See Also
    --------
    read_rsl_projections : Read RSL projections back into memory.
 
    Notes
    -----
    The dataset is written as-is: no validation is performed and no encoding
    or compression is applied.
    """
    projections.to_netcdf(output_file)

def read_rsl_projections(path: str)->xr.Dataset:
    """
    Read relative sea level projections into memory.
 
    Parameters
    ----------
    path : str
        Path to the NetCDF file holding the RSL projections.
 
    Returns
    -------
    xarray.Dataset
        Dataset holding the RSL projections.
 
    See Also
    --------
    write_rsl_projections : Write RSL projections to disk.
 
    Notes
    -----
    The dataset is opened lazily, so variable values are read from disk only
    when they are accessed.
    """
    return xr.open_dataset(path)

#---- Add your own functions to read/write additional data here ----#
