import redis

# function to synchronize start / end of benchmark across all pods


def redis_sync_pods(clients, timeout_sec, redis_host, syncpoint_name, logger, socket_port=6379):
    logger.debug("Redis channel %s timeout %d at %s:6379" % (syncpoint_name, timeout_sec, redis_host))
    r = redis.StrictRedis(redis_host, 6379, socket_timeout=timeout_sec)
    p = r.pubsub()
    p.subscribe(syncpoint_name)
    subscribers = int(r.pubsub_numsub(syncpoint_name)[0][1])
    if subscribers == clients:
        r.publish(syncpoint_name, "continue")
        logger.debug("published signal to go ahead with syncpoint %s" % syncpoint_name)
    logger.debug(
        "With %d subscribers, awaiting continue message on %s channel" % (subscribers, syncpoint_name)
    )
    for msg in p.listen():
        logger.debug("Complete message from channel: %s" % msg)
        if isinstance(msg["data"], bytes):
            if msg["data"].decode("utf-8") == "continue":
                logger.info("Continue message received on channel %s" % syncpoint_name)
                break
        else:
            logger.debug("msg data was not string")
    r.publish(syncpoint_name, "running")
    r.connection_pool.disconnect()
