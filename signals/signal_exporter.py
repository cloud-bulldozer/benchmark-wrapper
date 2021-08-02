from dataclasses import dataclass
from typing import Any, Dict, Tuple
import redis
import platform
import json
import time
import uuid


@dataclass
class Signal:
    """
    Standard event signal protocol. All required fields, defaults, and type
    restrictions are defined in this dataclass. Also includes a method for
    converting object data to json string.
    """

    publisher_id: str
    process_name: str
    event: str
    runner_host: str = platform.node()
    sample_no: int = -1
    tag: str = "No tag specified"
    metadata: Dict = None

    def __post_init__(self) -> None:
        """
        Checks all field types.
        """
        for (name, field_type) in self.__annotations__.items():
            if not isinstance(self.__dict__[name], field_type):
                if name == "metadata" and self.metadata == None:
                    continue
                raise TypeError(
                    f"The field {name} should be type {field_type}, not {type(self.__dict__[name])}"
                )

    def to_json_str(self) -> Dict[str, Any]:
        """
        Converts object data into json string.
        """
        result: Dict[str, Any] = {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("__") and k.endswith("__"))
            and not (k == "metadata" and v == None)
        }
        return json.dumps(result)


@dataclass
class Response:
    """
    Standard signal response protocol. All required fields, defaults, and type
    restrictions are defined in this dataclass. Also includes a method for 
    converting object data to json string.
    """

    tool_id: str
    publisher_id: str
    event: str
    ras: int

    def __post_init__(self) -> None:
        """
        Checks all field types.
        """
        for (name, field_type) in self.__annotations__.items():
            if not isinstance(self.__dict__[name], field_type):
                if name == "ras" and self.ras == None:
                    continue
                raise TypeError(
                    f"The field {name} should be type {field_type}, not {type(self.__dict__[name])}"
                )

    def to_json_str(self) -> Dict[str, Any]:
        """
        Converts object data into json string.
        """
        result: Dict[str, Any] = {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("__") and k.endswith("__"))
            and not (k == "ras" and v == None)
        }
        return json.dumps(result)


class SignalExporter:
    """
    A signal management object for tools that wish to publish event/state signals.
    Also handles subscriber recording and response reading/awaiting. Uses the standard
    signal protocol for all published messages. Easy-to-use interface for publishing
    legal signals and handling responders.
    """

    def __init__(
        self,
        process_name: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        runner_host: str = None,
    ) -> None:
        """
        Sets exporter object fields and generates unique publisher_id.
        Allows for specification of redis host/port. Also allows runner
        hostname to be inputted manually (otherwise will default to 
        platform.node() value)
        """
        self.subs = []
        self.proc_name = process_name
        self.runner_host = runner_host
        self.pub_id = process_name + "-" + str(uuid.uuid4())
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.init_listener = None
        self.legal_events = None

    def _sig_builder(
        self, event: str, sample: int = -1, tag: str = None, metadata: Dict = None
    ) -> Signal:
        """
        Build a signal data object based on exporter object fields,
        as well as user-inputted fields. Returns the signal object.
        """
        sig = Signal(publisher_id=self.pub_id, process_name=self.proc_name, event=event)
        sig.runner_host = self.runner_host if self.runner_host else sig.runner_host
        sig.tag = tag if tag else sig.tag
        sig.metadata = metadata if metadata else sig.metadata
        sig.sample_no = sample if sample >= 0 else sig.sample_no
        return sig

    def _get_data_dict(self, response: Dict) -> Dict:
        """
        Returns response signal payload if a properly-formed
        response is received. Otherwise return None.
        """
        if not "data" in response:
            print("No data in this response message")
            return None
        try:
            data = json.loads(response["data"])
        except ValueError:
            return None
        if "tool_id" not in data or "publisher_id" not in data or "event" not in data:
            print("Malformed response data found")
            return None
        return data

    def _fetch_responders(self) -> None:
        """
        Start initialization response listener. Add tool_ids from proper
        responses to the subscriber list.
        """
        subscriber = self.redis.pubsub(ignore_subscribe_messages=True)

        def _init_handler(item) -> None:
            data = self._get_data_dict(item)
            if (
                data
                and data["event"] == "initialization"
                and data["publisher_id"] == self.pub_id
            ):
                self.subs.append(data["tool_id"])

        subscriber.subscribe(**{"event-signal-response": _init_handler})
        self.init_listener = subscriber.run_in_thread()

    def _check_subs(self, event: str) -> Tuple[Any, list]:
        """
        Listen for responses from all registered subscribers. Return
        listener, as well as value based on responders' RAS codes.
        """
        if not self.subs:
            return None, [0]

        to_check = set(self.subs)
        subscriber = self.redis.pubsub(ignore_subscribe_messages=True)
        result_box = [0]

        def _sub_handler(item: Dict) -> None:
            data = self._get_data_dict(item)
            if data and data["publisher_id"] == self.pub_id and data["event"] == event:
                if "ras" in data:
                    to_check.remove(data["tool_id"])
                    if data["ras"] != 1:
                        print(
                            f"WARNING: Tool '{data['tool_id']}' returned bad response for event '{event}', ras: {data['ras']}"
                        )
                        result_box[0] = 1
            if not to_check:
                listener.stop()

        subscriber.subscribe(**{"event-signal-response": _sub_handler})
        listener = subscriber.run_in_thread()
        return listener, result_box

    def _valid_str_list(self, names: list) -> bool:
        """
        Return true if input is a non-empty list of strings. Otherwise
        return false.
        """
        return (
            bool(names)
            and isinstance(names, list)
            and all(isinstance(event, str) for event in names)
        )

    def publish_signal(
        self, event: str, sample: int = -1, tag: str = None, metadata: Dict = None
    ) -> int:
        """
        Publish a legal event signal. Includes additional options to specify sample_no,
        a tag, and any other additional metadata. Will then wait for responses from
        subscribed responders (if any). Returns one of the below result codes based on 
        signal publish/response success.

        RESULT CODES:
        0 = ALL SUBS RESPONDED WELL
        1 = SOME SUBS RESPONDED BADLY
        2 = NOT ALL SUBS RESPONDED
        3 = ILLEGAL EVENT NAME PASSED IN
        4 = INITIALIZATION SIGNAL ATTEMPTED, BAD
        5 = SHUTDOWN SIGNAL ATTEMPTED, BAD
        """
        skip_check = False
        if not self.init_listener or not self.init_listener.is_alive():
            print(
                "WARNING: Exporter is not initialized, not accepting subscribers and no event checking"
            )
            skip_check = True

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
        sub_check, result_box = self._check_subs(event)

        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())

        counter = 0
        while sub_check and sub_check.is_alive():
            time.sleep(0.1)
            counter += 1
            if counter >= 200:
                print("Timeout after waiting 20 seconds for sub response")
                return 2

        return result_box[0]

    def initialize(
        self, legal_events: list, tag: str = None, expected_hosts: list = None
    ) -> None:
        """
        Publishes an initialization message. Starts a listener that reads responses
        to the initialization message and adds responders to the subscriber list.
        Sets list of legal event names for future signals, and also allows for optional
        input of expected hostnames (subscribers) as well as a tag.
        """
        if not self._valid_str_list(legal_events):
            print("ERROR: 'legal_events' arg must be a list of string event names")
            return

        if expected_hosts:
            if not self._valid_str_list(expected_hosts):
                print("ERROR: 'expected_hosts' arg must be a list of string hostnames")
                return
            for host in expected_hosts:
                self.subs.append(host + "-resp")

        self.legal_events = legal_events
        sig = self._sig_builder(event="initialization", tag=tag)
        self._fetch_responders()
        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())

    def shutdown(self, tag: str = None) -> None:
        """
        Shuts down initialization response listener (stops accepting subscribers).
        Wipes the subscriber list and publishes a shutdown message.
        """
        sig = self._sig_builder(event="shutdown", tag=tag)
        self.init_listener.stop()
        self.subs = []
        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())


class SignalResponder:
    """
    A signal management object for tools that wish to respond to event/state signals.
    Can be used both for listening for signals as well as responding to them. Also
    allows for locking onto specific tags/publisher_ids. Uses the standard signal
    response protocol for all published messages.
    """

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379) -> None:
        """
        Sets exporter object fields and generates unique tool_id.
        Allows for specification of redis host/port.
        """
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.subscriber = self.redis.pubsub(ignore_subscribe_messages=True)
        self.subscriber.subscribe("event-signal-pubsub")
        self.tool_id = platform.node() + "-resp"  # ADD UUID HERE?
        self.locked_id = None
        self.locked_tag = None

    def _parse_signal(self, signal: Dict) -> Dict:
        """
        Validates received signal. Returns payload if valid.
        Also applies tag/publisher_id filters if added.
        """
        try:
            data = json.loads(signal["data"])
        except ValueError:
            return None
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
            if (not self.locked_id or self.locked_id == data["publisher_id"]) and (
                not self.locked_tag or self.locked_tag == data["tag"]
            ):
                return data
        return None

    def listen(self):
        """
        Yield all legal published signals. If a specific tag/published_id
        was locked, only signals with those matching values will be yielded.
        """
        for item in self.subscriber.listen():
            data = self._parse_signal(item)
            if data:
                yield data

    def respond(self, publisher_id: str, event: str, ras: int = None) -> None:
        """
        Publish a legal response to a certain publisher_id's event signal.
        Also allows for optional ras code to be added on (required for 
        publisher acknowledgement, but not for initialization response).
        """
        response = Response(self.tool_id, publisher_id, event, ras)
        self.redis.publish("event-signal-response", response.to_json_str())

    def lock_id(self, publisher_id: str) -> None:
        """
        Lock onto a specific publisher_id. Only receive signals from the
        chosen id.
        """
        if isinstance(publisher_id, str):
            self.locked_id == publisher_id
        else:
            print("Unsuccessful lock, 'publisher_id' must be type str")

    def lock_tag(self, tag: str) -> None:
        """
        Lock onto a specific tag. Only receive signals from the chosen tag.
        """
        if isinstance(tag, str):
            self.locked_tag == tag
        else:
            print("Unsuccessful lock, 'tag' must be type str")
