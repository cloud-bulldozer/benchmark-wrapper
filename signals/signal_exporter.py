from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
import redis
import random
import platform
import threading
import json


@dataclass
class Signal:
    benchmark_id: str
    benchmark_name: str
    event: str
    runner_host: str = platform.node()
    sample_no: int = -1
    user: str = "No user specified"  # Could also be "tag"

    def __post_init__(self):
        for (name, field_type) in self.__annotations__.items():
            if not isinstance(self.__dict__[name], field_type):
                raise TypeError(
                    f"The field {name} should be type {field_type}, not {type(self.__dict__[name])}"
                )

        legal_events = [
            "initialization",
            "benchmark-start",
            "benchmark-stop",
            "sample-start",
            "sample-stop",
            "shutdown"
        ]
        if self.event not in legal_events:
            print(f"Event {self.event} not one of legal events: {legal_events}")
            exit(1)

    def to_json_str(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("__") and k.endswith("__"))
        }
        return json.dumps(result)


class SignalExporter:
    def __init__(self, benchmark_name, redis_host="localhost", redis_port=6379) -> None:
        self.subs = []
        self.bench_name = benchmark_name
        self.bench_id = benchmark_name + datetime.now().strftime(
            f"%m%d%Y%H%M%Sr{random.randint(1000,9999)}"
        )
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.init_listener = None

    def _get_data_dict(self, response):
        if not "data" in response:
            print("No data in this response message")
            return None
        if isinstance(response["data"], int):
            return None
        data = json.loads(response["data"])
        if "tool_id" not in data or "benchmark_id" not in data or "event" not in data:
            print("Malformed response data found")
            return None
        return data

    def _fetch_responders(self):
        # Check for responses to initialization
        subscriber = self.redis.pubsub(ignore_subscribe_messages=True)

        def _init_handler(item):
            data = self._get_data_dict(item)
            if (
                data
                and data["event"] == "initialization"
                and data["benchmark_id"] == self.bench_id
            ):
                self.subs.append(data["tool_id"])

        subscriber.subscribe(**{"benchmark-signal-response": _init_handler})
        self.init_listener = subscriber.run_in_thread()

    def _check_subs(self):
        to_check = set(self.subs)
        subscriber = self.redis.pubsub(ignore_subscribe_messages=True)
        subscriber.subscribe("benchmark-signal-response")
        for item in subscriber.listen():
            data = self._get_data_dict(item)
            if data and 'ras' in data and data['ras'] == 1:
                to_check.remove(data['tool_id'])
            if not to_check:
                break
        return 0

    def publish_signal(
        self, event, runner_host=None, sample: int = -1, user=None
    ) -> int:
        # NOTE: runner_host will be automatically populated w/ platform.node() if nothing is passed in

        # Unsure if necessary twice vvv
        legal_events = [
            "initialization",
            "benchmark-start",
            "benchmark-stop",
            "sample-start",
            "sample-stop",
            "shutdown"
        ]

        if not event in legal_events:
            print(f"Event {self.event} not one of legal events: {legal_events}")
            exit(1)
        # End of unecessary(?) ^^^

        sig = Signal(
            benchmark_id=self.bench_id, benchmark_name=self.bench_name, event=event
        )
        sig.runner_host = runner_host if runner_host else sig.runner_host
        sig.user = user if user else sig.user
        sig.sample_no = sample if sample >= 0 else sig.sample_no

        # publish
        self.redis.publish(channel="benchmark-signal-pubsub", message=sig.to_json_str())

        """
        RESULT CODES:
        0 = ALL SUBS RESPONDED WELL
        1 = SOME SUBS RESPONDED BADLY
        2 = NOT ALL SUBS RESPONDED
        3 = INITIALIZATION SIGNAL PUBLISHED, LISTENING
        4 = INITIALIZATION SIGNAL NOT PUBLISHED, ALREADY LISTENING
        5 = SHUTDOWN SIGNAL PUNISHED, NO LONGER LISTENING
        """

        if event == "initialization":
            if self.init_listener and self.init_listener.is_alive():
                print("Already published initialization signal for this benchmark")
                result = 4
            else:
                self._fetch_responders()
                result = 3
        elif event == "shutdown":
            self.init_listener.stop()
            result = 5
        else:
            result = self._check_subs()
        return result
