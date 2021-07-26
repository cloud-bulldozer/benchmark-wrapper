from dataclasses import dataclass
from datetime import datetime
from typing import Any, Counter, Dict
import redis
import random
import platform
import json
import time


@dataclass
class Signal:
    benchmark_id: str
    benchmark_name: str
    event: str
    runner_host: str = platform.node()
    sample_no: int = -1
    tag: str = "No tag specified"  # Could also be "user"
    metadata: Dict = None

    def __post_init__(self):
        for (name, field_type) in self.__annotations__.items():
            if not isinstance(self.__dict__[name], field_type):
                if name == "metadata" and self.metadata == None:
                    continue
                raise TypeError(
                    f"The field {name} should be type {field_type}, not {type(self.__dict__[name])}"
                )

        legal_events = [
            "initialization",
            "benchmark-start",
            "benchmark-stop",
            "sample-start",
            "sample-stop",
            "shutdown",
        ]
        if self.event not in legal_events:
            print(f"Event {self.event} not one of legal events: {legal_events}")
            exit(1)

    def to_json_str(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("__") and k.endswith("__"))
            and not (k == "metadata" and v == None)
        }
        return json.dumps(result)


@dataclass
class Response:
    tool_id: str
    benchmark_id: str
    event: str
    ras: int

    def __post_init__(self):
        for (name, field_type) in self.__annotations__.items():
            if not isinstance(self.__dict__[name], field_type):
                if name == "ras" and self.ras == None:
                    continue
                raise TypeError(
                    f"The field {name} should be type {field_type}, not {type(self.__dict__[name])}"
                )

        legal_events = [
            "initialization",
            "benchmark-start",
            "benchmark-stop",
            "sample-start",
            "sample-stop",
            "shutdown",
        ]
        if self.event not in legal_events:
            print(f"Event {self.event} not one of legal events: {legal_events}")
            exit(1)

    def to_json_str(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("__") and k.endswith("__"))
            and not (k == "ras" and v == None)
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
        if not self.subs:
            return 0

        to_check = set(self.subs)
        subscriber = self.redis.pubsub(ignore_subscribe_messages=True)

        def _sub_handler(item):
            data = self._get_data_dict(item)
            if data and "ras" in data and data["ras"] == 1:
                to_check.remove(data["tool_id"])
            if not to_check:
                listener.stop()

        subscriber.subscribe(**{"benchmark-signal-response": _sub_handler})
        listener = subscriber.run_in_thread()
        return listener

    def publish_signal(
        self, event, runner_host=None, sample: int = -1, tag=None, metadata=None
    ) -> int:
        # NOTE: runner_host will be automatically populated w/ platform.node() if nothing is passed in

        # Unsure if necessary twice vvv
        legal_events = [
            "initialization",
            "benchmark-start",
            "benchmark-stop",
            "sample-start",
            "sample-stop",
            "shutdown",
        ]

        if not event in legal_events:
            print(f"Event {self.event} not one of legal events: {legal_events}")
            exit(1)
        # End of unecessary(?) ^^^

        sig = Signal(
            benchmark_id=self.bench_id, benchmark_name=self.bench_name, event=event
        )
        sig.runner_host = runner_host if runner_host else sig.runner_host
        sig.tag = tag if tag else sig.tag
        sig.metadata = metadata if metadata else sig.metadata
        sig.sample_no = sample if sample >= 0 else sig.sample_no

        """
        RESULT CODES:
        0 = ALL SUBS RESPONDED WELL
        1 = SOME SUBS RESPONDED BADLY
        2 = NOT ALL SUBS RESPONDED
        3 = INITIALIZATION SIGNAL PUBLISHED, LISTENING
        4 = INITIALIZATION SIGNAL NOT PUBLISHED, ALREADY LISTENING
        5 = SHUTDOWN SIGNAL PUNISHED, NO LONGER LISTENING
        """

        sub_check = None
        result = 0
        if event == "initialization":
            if self.init_listener and self.init_listener.is_alive():
                print("Already published initialization signal for this benchmark, never shut down")
                return 4
            else:
                self._fetch_responders()
                result = 3
        elif event == "shutdown":
            self.init_listener.stop()
            result = 5
        else:
            sub_check = self._check_subs()

        self.redis.publish(channel="benchmark-signal-pubsub", message=sig.to_json_str())
        
        counter = 0
        while sub_check and sub_check.is_alive():
            time.sleep(0.1)
            counter += 1
            if counter >= 200:
                print("Timeout after waiting 20 seconds for sub response")
                result = 2
                break

        return result


class SignalResponder:
    def __init__(self, redis_host="localhost", redis_port=6379) -> None:
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.subscriber = self.redis.pubsub(ignore_subscribe_messages=True)
        self.subscriber.subscribe("benchmark-signal-pubsub")
        self.tool_id = platform.node() + "-resp"

    def _parse_signal(self, signal):
        data = json.loads(signal["data"])
        # FIXME - Replace below line, maybe with dataclasses.fields()?
        check_set = set(
            [
                "benchmark_id",
                "benchmark_name",
                "event",
                "runner_host",
                "sample_no",
                "tag",
                "metadata"
            ]
        )
        if set(data.keys()) == check_set or check_set - set(data.keys()) == {"metadata"}:
            return data
        return None

    def listen(self):
        for item in self.subscriber.listen():
            data = self._parse_signal(item)
            if data:
                yield data

    def respond(self, benchmark_id, event, ras=None):
        response = Response(self.tool_id, benchmark_id, event, ras)
        self.redis.publish("benchmark-signal-response", response.to_json_str())
