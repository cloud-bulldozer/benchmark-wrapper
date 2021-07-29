from dataclasses import dataclass
from typing import Any, Dict
import redis
import platform
import json
import time
import uuid


@dataclass
class Signal:
    publisher_id: str
    process_name: str
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
    publisher_id: str
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

    def to_json_str(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("__") and k.endswith("__"))
            and not (k == "ras" and v == None)
        }
        return json.dumps(result)


class SignalExporter:
    def __init__(
        self, process_name, redis_host="localhost", redis_port=6379, runner_host=None
    ) -> None:
        # NOTE: runner_host will be automatically populated w/ platform.node() if nothing is passed in
        self.subs = []
        self.proc_name = process_name
        self.runner_host = runner_host
        self.pub_id = process_name + "-" + str(uuid.uuid4())
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.init_listener = None
        self.legal_events = None

    def _sig_builder(self, event, sample=-1, tag=None, metadata=None):
        sig = Signal(publisher_id=self.pub_id, process_name=self.proc_name, event=event)
        sig.runner_host = self.runner_host if self.runner_host else sig.runner_host
        sig.tag = tag if tag else sig.tag
        sig.metadata = metadata if metadata else sig.metadata
        sig.sample_no = sample if sample >= 0 else sig.sample_no
        return sig

    def _get_data_dict(self, response):
        if not "data" in response:
            print("No data in this response message")
            return None
        if isinstance(response["data"], int):
            return None
        data = json.loads(response["data"])
        if "tool_id" not in data or "publisher_id" not in data or "event" not in data:
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
                and data["publisher_id"] == self.pub_id
            ):
                self.subs.append(data["tool_id"])

        subscriber.subscribe(**{"event-signal-response": _init_handler})
        self.init_listener = subscriber.run_in_thread()

    def _check_subs(self, event):
        if not self.subs:
            return 0

        to_check = set(self.subs)
        subscriber = self.redis.pubsub(ignore_subscribe_messages=True)

        def _sub_handler(item):
            data = self._get_data_dict(item)
            # FIXME - Needs more checks (publisher ID, event)
            if data and data["publisher_id"] == self.pub_id and data["event"] == event:
                if "ras" in data and data["ras"] == 1:
                    to_check.remove(data["tool_id"])
            if not to_check:
                listener.stop()

        subscriber.subscribe(**{"event-signal-response": _sub_handler})
        listener = subscriber.run_in_thread()
        return listener

    def _valid_event_list(self, events):
        return (
            bool(events)
            and isinstance(events, list)
            and all(isinstance(event, str) for event in events)
        )

    def publish_signal(self, event, sample: int = -1, tag=None, metadata=None) -> int:
        skip_check = False
        if not self.init_listener or not self.init_listener.is_alive():
            print(
                "WARNING: Exporter is not initialized, not accepting subscribers and no event checking"
            )
            skip_check = True

        """
        RESULT CODES:
        0 = ALL SUBS RESPONDED WELL
        1 = SOME SUBS RESPONDED BADLY
        2 = NOT ALL SUBS RESPONDED
        3 = ILLEGAL EVENT NAME PASSED IN
        4 = INITIALIZATION SIGNAL ATTEMPTED, BAD
        5 = SHUTDOWN SIGNAL ATTEMPTED, BAD
        """

        if event == "initialization":
            print(
                "ERROR: Please use the 'initialize()' method for publishing initialization signals"
            )
            return 4

        if event == "shutdown":
            print("ERROR: Please use the 'shutdown()' method for shutdown signals")
            return 5

        if not skip_check and not event in self.legal_events:
            print(f"Event {self.event} not one of legal events: {self.legal_events}")
            return 3

        sig = self._sig_builder(event=event, sample=sample, tag=tag, metadata=metadata)
        result = 0
        sub_check = self._check_subs(event)

        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())

        counter = 0
        while sub_check and sub_check.is_alive():
            time.sleep(0.1)
            counter += 1
            if counter >= 200:
                print("Timeout after waiting 20 seconds for sub response")
                result = 2
                break

        return result

    def initialize(self, legal_events, tag=None):
        if not self._valid_event_list(legal_events):
            print("'legal_events' arg must be a list of strings")

        self.legal_events = legal_events
        sig = self._sig_builder(event="initialization", tag=tag)
        self._fetch_responders()
        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())

    def shutdown(self, tag=None):
        sig = self._sig_builder(event="shutdown", tag=tag)
        self.init_listener.stop()
        self.subs = []
        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())


class SignalResponder:
    def __init__(self, redis_host="localhost", redis_port=6379) -> None:
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.subscriber = self.redis.pubsub(ignore_subscribe_messages=True)
        self.subscriber.subscribe("event-signal-pubsub")
        self.tool_id = platform.node() + "-resp"  # ADD UUID HERE?

    def _parse_signal(self, signal):
        data = json.loads(signal["data"])
        # FIXME - Replace below line, maybe with dataclasses.fields()?
        check_set = set(
            [
                "publisher_id",
                "process_name",
                "event",
                "runner_host",
                "sample_no",
                "tag",
                "metadata",
            ]
        )
        if set(data.keys()) == check_set or check_set - set(data.keys()) == {
            "metadata"
        }:
            return data
        return None

    def listen(self):
        for item in self.subscriber.listen():
            data = self._parse_signal(item)
            if data:
                yield data

    def respond(self, publisher_id, event, ras=None):
        response = Response(self.tool_id, publisher_id, event, ras)
        self.redis.publish("event-signal-response", response.to_json_str())
