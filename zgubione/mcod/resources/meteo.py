import logging

import netCDF4

logger = logging.getLogger("mcod")


def is_valid_netcdf(path):
    try:
        netCDF4.Dataset(path)
        return True
    except Exception as exc:
        logger.debug("Exception during NetCDF validation: {}".format(exc))
    return False


def check_meteo_data(content_type, path, file_info):
    if content_type in ["x-hdf", "octet-stream"] and is_valid_netcdf(path):
        content_type = "netcdf"
    elif content_type == "octet-stream" and "Gridded binary" in file_info:
        content_type = "x-grib"
    return content_type
