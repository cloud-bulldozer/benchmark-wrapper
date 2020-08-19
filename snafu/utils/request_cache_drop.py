# this module accepts environment variables which control
# cache dropping behavior
# cache dropping is implemented by privileged pods separate from
# the benchmark pods, and these are invoked by
# HTTP GET from here.
# if no environment variables are defined, nothing happens

import os
import http.client
import logging


def getPortNum(envVar, defaultPort):
    portStr = os.getenv(envVar)
    if portStr is not None:
        return int(portStr)
    return defaultPort


class RunSnafuCacheDropException(Exception):
    pass


dropKernelCachePort = getPortNum('KCACHE_DROP_PORT_NUM', 9435)
dropCephCachePort = getPortNum('CEPH_CACHE_DROP_PORT_NUM', 9437)

logger = logging.getLogger("snafu")

dbgLevel = os.getenv('DROP_CACHE_DEBUG_LEVEL')
if dbgLevel is not None:
    logger.setLevel(logging.DEBUG)
    logger.info('drop_cache debug log level')

http_debug_level = int(os.getenv('HTTP_DEBUG_LEVEL', default=0))

http_timeout = 10


# drop Ceph OSD cache if requested to

def drop_cache():
    ceph_cache_drop_pod_ip = os.getenv('ceph_drop_pod_ip')
    logger.info('ceph OSD cache drop pod: %s' % str(ceph_cache_drop_pod_ip))
    if ceph_cache_drop_pod_ip is not None:
        conn = http.client.HTTPConnection(ceph_cache_drop_pod_ip,
                                          port=dropCephCachePort,
                                          timeout=http_timeout)
        if http_debug_level > 0:
            conn.set_debuglevel(http_debug_level)
        logger.info('requesting ceph to drop cache via %s:%d' %
                    (ceph_cache_drop_pod_ip, dropCephCachePort))
        conn.request('GET', '/DropCephCache')
        rsp = conn.getresponse()
        if rsp.status != http.client.OK:
            logger.error('HTTP ERROR %d: %s' % (rsp.status, rsp.reason))
            raise RunSnafuCacheDropException('Ceph OSD cache drop %s:%d' %
                                             (ceph_cache_drop_pod_ip,
                                              dropCephCachePort))

    # drop kernel cache if requested to

    kernel_cache_drop_pod_ips = os.getenv('kcache_drop_pod_ips')
    logger.info('kernel cache drop pods: %s' % str(kernel_cache_drop_pod_ips))
    if kernel_cache_drop_pod_ips is not None:
        pod_ip_list = kernel_cache_drop_pod_ips.split()
        for ip in pod_ip_list:
            conn = http.client.HTTPConnection(ip,
                                              port=dropKernelCachePort,
                                              timeout=http_timeout)
            if http_debug_level > 0:
                conn.set_debuglevel(http_debug_level)
            logger.info('requesting kernel to drop cache via %s:%d' %
                        (ip, dropKernelCachePort))
            conn.request('GET', '/DropKernelCache')
            rsp = conn.getresponse()
            if rsp.status != http.client.OK:
                logger.error('HTTP code %d: %s' % (rsp.status, rsp.reason))
                raise RunSnafuCacheDropException('kernel cache drop %s:%d' %
                                                 (ip, dropKernelCachePort))


if __name__ == '__main__':
    drop_cache()
