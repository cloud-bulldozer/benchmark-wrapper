#!/usr/bin/env python

import subprocess
import logging
import cherrypy

stdout_log = open('/tmp/dropcache.log', 'w')

logger = logging.getLogger('dropcache')

class DropOSDCache(object):
    @cherrypy.expose
    #@cherrypy.tools.json_out()
    #@cherrypy.tools.json_in()

    def drop_osd_caches(self):
        try:
            result = subprocess.check_output(
                ["/bin/sh", "drop-osd-cache-within-toolbox.sh"])
        except subprocess.CalledProcessError as e:
            logger.error('failed to drop cache')
            logger.exception(e)
            return 'FAIL'
        logger.info(result)
        return 'SUCCESS'

if __name__ == '__main__':
    try:
        result = subprocess.Popen(
            ["/bin/sh", "-c", "/usr/local/bin/toolbox.sh"])
    except subprocess.CalledProcessError as e:
        logger.error('failed to source toolbox')
        logger.exception(e)
    config = { 
        'global': {
            'server.socket_host': '0.0.0.0' ,
            'server.socket_port': 9432,
        },
    }
    cherrypy.config.update(config)
    cherrypy.quickstart(DropOSDCache())
