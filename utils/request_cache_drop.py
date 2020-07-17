# this module accepts environment variables which control
# cache dropping behavior
# cache dropping is implemented by privileged pods separate from
# the benchmark pods, and these are invoked by 
# HTTP GET from here.
# if no environment variables are defined, nothing happens

import os
import http.client
import sys
import logging

dropKernelCachePort = 9435  # FIXME: hardcoded for now
dropCephCachePort = 9437  # FIXME: hardcoded for now
logger = logging.getLogger("snafu")

dbgLevel = os.getenv('DROP_CACHE_DEBUG_LEVEL') 
if dbgLevel != None:
    logger.setLevel(logging.DEBUG)
    logger.info('drop_cache debug log level')

http_debug_level = int(os.getenv('HTTP_DEBUG_LEVEL', default=0))

http_timeout = 2

def drop_cache():
    kernel_cache_drop_pod_ips = os.getenv('kcache_drop_pod_ips')
    logger.info('kernel cache drop pods: %s' % str(kernel_cache_drop_pod_ips))
    ceph_cache_drop_pod_ip = os.getenv('ceph_drop_pod_ip')
    logger.info('ceph OSD cache drop pod: %s' % str(ceph_cache_drop_pod_ip))
    if kernel_cache_drop_pod_ips != None:
        pod_ip_list = kernel_cache_drop_pod_ips.split()
        for ip in pod_ip_list:
            conn = http.client.HTTPConnection(ip, port=dropKernelCachePort, timeout=http_timeout)
            if http_debug_level > 0:
                conn.set_debuglevel(http_debug_level)
            logger.info('requesting kernel to drop cache via %s:%d' % (ip, dropKernelCachePort))
            try:
                conn.request('GET', '/DropKernelCache')
                rsp = conn.getresponse()
                if rsp.status != http.client.OK:
                    logger.error('HTTP code %d: %s' % (rsp.status, rsp.reason))
                    raise RunSnafuCacheDropException(ip, dropKernelCachePort)
            except http.client.HTTPException as e:
                logger.error('failed to request kernel cache drop' % (rsp.status, rsp.reason))
                logger.exception(e)
                raise e
            except TimeoutError as e:
                logger.error('timeout requesting kernel cache drop')
                logger.exception(e)
                raise e

    if ceph_cache_drop_pod_ip != None:
        conn = http.client.HTTPConnection(ceph_cache_drop_pod_ip, port=dropKernelCachePort, timeout=http_timeout)
        if http_debug_level > 0:
            conn.set_debuglevel(http_debug_level)
        logger.info('requesting ceph to drop cache via %s:%d' % (ip, dropCephCachePort))
        try:
            conn.request('GET', '/DropCephCache')
            rsp = conn.getresponse()
            if rsp.status != http_ok:
                logger.error('HTTP ERROR %d: %s' % (rsp.status, rsp.reason))
                raise RunSnafuCacheDropException('Ceph OSDs', ip, dropKernelCachePort)
        except http.client.HTTPException as e:
            logger.error('failed to request Ceph OSD cache drop' % (rsp.status, rsp.reason))
            logger.exception(e)
            raise e
        except TimeoutError as e:
            logger.error('timeout requesting kernel cache drop')
            logger.exception(e)
            raise e

if __name__ == '__main__':
    drop_cache()
