
# from backpack_wrapper.backpack_wrapperimport backpack_wrapper
from snafu.vegeta_wrapper.vegeta_wrapper import vegeta_wrapper
from snafu.fio_wrapper.fio_wrapper import fio_wrapper
from snafu.smallfile_wrapper.smallfile_wrapper import smallfile_wrapper
from snafu.uperf_wrapper.uperf_wrapper import uperf_wrapper
from snafu.pgbench_wrapper.pgbench_wrapper import pgbench_wrapper
from snafu.fs_drift_wrapper.fs_drift_wrapper import fs_drift_wrapper
from snafu.cluster_loader.cluster_loader import cluster_loader_wrapper
from snafu.hammerdb.hammerdb_wrapper import hammerdb_wrapper
from snafu.ycsb_wrapper.ycsb_wrapper import ycsb_wrapper
from snafu.scale_openshift_wrapper.scale_openshift_wrapper import scale_openshift_wrapper

import logging
logger = logging.getLogger("snafu")

wrapper_dict = {
    "fio": fio_wrapper,
    "smallfile": smallfile_wrapper,
    "fs-drift": fs_drift_wrapper,
    "cl": cluster_loader_wrapper,
    "hammerdb": hammerdb_wrapper,
    "ycsb": ycsb_wrapper,
    "uperf": uperf_wrapper,
    "pgbench": pgbench_wrapper,
    "vegeta": vegeta_wrapper,
    "scale": scale_openshift_wrapper
}
#    "backpack": pgbench_wrapper,
#    "fio": fio_wrapper,
#    "uperf": uperf_wrapper
#    }

def wrapper_factory(tool_name, parser):
    try:
        wrapper = wrapper_dict[tool_name]
        logger.info("identified %s as the benchmark wrapper" % tool_name)
    except KeyError:
        logger.error("Tool name %s is not recognized." % tool_name)
        return 1  # if error return 1 and fail
    else:
        return wrapper(parser)
