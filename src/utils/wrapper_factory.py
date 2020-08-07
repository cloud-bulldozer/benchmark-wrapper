
# from backpack_wrapper.backpack_wrapperimport backpack_wrapper
from vegeta_wrapper.vegeta_wrapper import vegeta_wrapper
from fio_wrapper.fio_wrapper import fio_wrapper
from smallfile_wrapper.smallfile_wrapper import smallfile_wrapper
from uperf_wrapper.uperf_wrapper import uperf_wrapper
from flent_wrapper.flent_wrapper import flent_wrapper
from pgbench_wrapper.pgbench_wrapper import pgbench_wrapper
from fs_drift_wrapper.fs_drift_wrapper import fs_drift_wrapper
from cluster_loader.cluster_loader import cluster_loader_wrapper
from hammerdb.hammerdb_wrapper import hammerdb_wrapper
from ycsb_wrapper.ycsb_wrapper import ycsb_wrapper

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
    "flent": flent_wrapper
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
