import logging

from snafu.cyclictest_wrapper.cyclictest_wrapper import cyclictest_wrapper
from snafu.dns_perf_wrapper.dns_perf_wrapper import dns_perf_wrapper
from snafu.fio_wrapper.fio_wrapper import fio_wrapper
from snafu.flent_wrapper.flent_wrapper import flent_wrapper
from snafu.fs_drift_wrapper.fs_drift_wrapper import fs_drift_wrapper
from snafu.hammerdb.hammerdb_wrapper import hammerdb_wrapper
from snafu.image_pull_wrapper.image_pull_wrapper import image_pull_wrapper
from snafu.log_generator_wrapper.log_generator_wrapper import log_generator_wrapper
from snafu.oslat_wrapper.oslat_wrapper import oslat_wrapper
from snafu.pgbench_wrapper.pgbench_wrapper import pgbench_wrapper
from snafu.registry import TOOLS
from snafu.scale_openshift_wrapper.scale_openshift_wrapper import scale_openshift_wrapper
from snafu.smallfile_wrapper.smallfile_wrapper import smallfile_wrapper
from snafu.stressng_wrapper.stressng_wrapper import stressng_wrapper
from snafu.sysbench_wrapper.sysbench_wrapper import sysbench_wrapper
from snafu.trex_wrapper.trex_wrapper import trex_wrapper
from snafu.upgrade_openshift_wrapper.upgrade_openshift_wrapper import upgrade_openshift_wrapper
from snafu.vegeta_wrapper.vegeta_wrapper import vegeta_wrapper
from snafu.ycsb_wrapper.ycsb_wrapper import ycsb_wrapper

logger = logging.getLogger("snafu")

wrapper_dict = {
    "fio": fio_wrapper,
    "smallfile": smallfile_wrapper,
    "fs-drift": fs_drift_wrapper,
    "hammerdb": hammerdb_wrapper,
    "ycsb": ycsb_wrapper,
    "pgbench": pgbench_wrapper,
    "vegeta": vegeta_wrapper,
    "scale": scale_openshift_wrapper,
    "stressng": stressng_wrapper,
    "upgrade": upgrade_openshift_wrapper,
    "cyclictest": cyclictest_wrapper,
    "oslat": oslat_wrapper,
    "trex": trex_wrapper,
    "flent": flent_wrapper,
    "log_generator": log_generator_wrapper,
    "image_pull": image_pull_wrapper,
    "sysbench": sysbench_wrapper,
    "dns_perf": dns_perf_wrapper,
}


def wrapper_factory(tool_name, parser):
    logger.debug("looking for %s" % tool_name)
    if TOOLS.get(tool_name, None) is not None:
        wrapper = TOOLS[tool_name]
        wrapper_obj = wrapper()
    elif wrapper_dict.get(tool_name, None) is not None:
        wrapper = wrapper_dict[tool_name]
        wrapper_obj = wrapper(parser)
    else:
        wrapper = None
        wrapper_obj = None

    if wrapper is not None:
        logger.info("identified %s as the benchmark wrapper" % tool_name)
        return wrapper_obj
    else:
        logger.error("Tool name %s is not recognized." % tool_name)
        return 1  # if error return 1 and fail
