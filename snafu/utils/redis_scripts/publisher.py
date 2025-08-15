#!/usr/bin/python

import argparse
import sys
import time
import traceback

import redis


def run_publisher(redis_host, redis_port, benchmark, pod_count):
    try:
        r = redis.StrictRedis(host=redis_host, port=redis_port)
        count = 0
        while count != pod_count:
            redis_command = f"PUBSUB NUMSUB {benchmark}"
            count = r.execute_command(redis_command)[1]
            print(count)
            time.sleep(1)
        print(r"All Pods are ready to run.Triggering the run.....\(^_^)/")  # noqa
        r.publish(benchmark, "run")
        return True
    except Exception as e:
        print("******Exception Occured*******")
        print(str(e))
        print(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(prog="Redis Publisher")
    parser.add_argument(
        "--redis-host", help="input the redis server address. DEFAULT: localhost", default="localhost"
    )
    parser.add_argument("--redis-port", help="input the redis port. DEFAULT: 6379", default=6379, type=int)
    parser.add_argument("benchmark", help="input the benchmark to be executed", type=str)
    parser.add_argument("pod_count", help="input the number of subscriber pods", type=int)
    # parser.add_argument("--help")
    args = parser.parse_args()
    redis_host = args.redis_host
    redis_port = args.redis_port
    benchmark = args.benchmark
    pod_count = args.pod_count
    run_publisher(redis_host, redis_port, benchmark, pod_count)


if __name__ == "__main__":
    sys.exit(main())
