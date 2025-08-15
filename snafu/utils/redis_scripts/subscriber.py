#!/usr/bin/python

import argparse
import sys
import time
import traceback

import redis


def run_subscriber(redis_host, redis_port, benchmark):
    try:
        r = redis.StrictRedis(host=redis_host, port=redis_port)

        p = r.pubsub()
        p.subscribe(benchmark)
        STATE = True
        count = 1

        while STATE:
            print(f"Waiting For all {benchmark} Pods to get ready ...{count}")
            count += 1
            message = p.get_message()
            if message:
                command = message["data"]
                if command == b"run":
                    STATE = False

            time.sleep(1)

        print(f"Executing {benchmark}...")
        return True
    except Exception as e:
        print("******Exception Occured*******")
        print(str(e))
        print(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(prog="Redis Subscriber")
    parser.add_argument(
        "--redis-host",
        help="input the redis server address. DEFAULT: localhost",
        default="localhost",
        type=str,
    )
    parser.add_argument("--redis-port", help="input the redis port. DEFAULT: 6379", default=6379, type=int)
    parser.add_argument("benchmark", help="input the benchmark to be executed", type=str)
    args = parser.parse_args()
    redis_host = args.redis_host
    redis_port = args.redis_port
    benchmark = args.benchmark
    run_subscriber(redis_host, redis_port, benchmark)


if __name__ == "__main__":
    sys.exit(main())
