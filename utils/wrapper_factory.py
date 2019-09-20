
#from backpack_wrapper.backpack_wrapperimport backpack_wrapper
from fio_wrapper.fio_wrapper import fio_wrapper
from smallfile_wrapper.smallfile_wrapper import smallfile_wrapper
#from pgbench_wrapper.pgbench_wrapper import pgbench_wrapper
from uperf_wrapper.uperf_wrapper import uperf_wrapper
from fs_drift_wrapper.fs_drift_wrapper import fs_drift_wrapper

import logging
logger = logging.getLogger("snafu")

wrapper_dict = {
    "fio": fio_wrapper,
    "smallfile": smallfile_wrapper,
    "fs-drift": fs_drift_wrapper,
    "uperf": uperf_wrapper
}
#    "backpack": pgbench_wrapper,
#    "fio": fio_wrapper,
#    "pgbench": pgbench_wrapper,
#    
#    }

def wrapper_factory(tool_name, parser):
    try:
        wrapper = wrapper_dict[tool_name]
        logger.info("identified %s as the benchmark wrapper" % tool_name) 
    except KeyError:
        logger.error("Tool name %s is not recognized." % tool_name)
        return 1 #if error return 1 and fail
    else:
        return wrapper(parser)
