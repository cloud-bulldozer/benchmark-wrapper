#!/usr/bin/python

import redis

class RedisUtils:
    def __init__(self, redis_host, redis_port):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_cache = redis.Redis(host=self.redis_host, port=self.redis_port)

    def set_code(self, test_name, test_args, test_status_code,):
        self.redis_cache.hset(test_name, test_args, test_status_code)
