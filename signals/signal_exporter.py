from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import redis
import platform
import json
import time
import uuid
import logging


def _create_logger(
    class_name: str, process_name: str, log_level: str
) -> logging.Logger:
    """
    Creates and returns logging.Logger object for detailed logging.
    Used by SignalExporter and SignalResponder.
    """
    logger = logging.getLogger(class_name).getChild(process_name)
    try:
        logger.setLevel(log_level)
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    except ValueError:
        raise ValueError("Legal log levels: [DEBUG, INFO, WARNING, ERROR, CRITICAL]")
    return logger


class ResultCodes(Enum):
    ALL_SUBS_SUCCESS = 0
    SUB_FAILED = 1
    MISSING_RESPONSE = 2


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
    runner_host: str
    sample_no: int = -1
    tag: str = "No tag specified"
    metadata: Optional[Dict] = None

    def __post_init__(self) -> None:
        """
        Checks all field types.
        """
        for (name, field_type) in self.__annotations__.items():
            if name == "metadata":
                field_type = field_type.__args__
            if not isinstance(self.__dict__[name], field_type):
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

    responder_id: str
    publisher_id: str
    event: str
    ras: Optional[int]

    def __post_init__(self) -> None:
        """
        Checks all field types.
        """
        for (name, field_type) in self.__annotations__.items():
            if name == "ras":
                field_type = field_type.__args__
            if not isinstance(self.__dict__[name], field_type):
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
        runner_host: str = platform.node(),
        log_level: str = "INFO",
    ) -> None:
        """
        Sets exporter object fields and generates unique publisher_id.
        Allows for specification of redis host/port. Also allows runner
        hostname to be inputted manually (otherwise will default to 
        platform.node() value)
        """
        self.logger = _create_logger("SignalExporter", process_name, log_level)
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
        config = {
            "publisher_id": self.pub_id,
            "process_name": self.proc_name,
            "event": event,
            "runner_host": self.runner_host,
        }
        if sample:
            config["sample_no"] = sample
        if tag:
            config["tag"] = tag
        if metadata:
            config["metadata"] = metadata
        sig = Signal(**config)
        return sig

    def _get_data_dict(self, response: Dict) -> Dict:
        """
        Returns response signal payload if a properly-formed
        response is received. Otherwise return None.
        """
        if not "data" in response:
            self.logger.debug(f"No data in this response message: {response}")
            return None
        try:
            data = json.loads(response["data"])
        except ValueError:
            return None
        if (
            "responder_id" not in data
            or "publisher_id" not in data
            or "event" not in data
        ):
            self.logger.debug(f"Malformed response data found: {response}")
            return None
        return data

    def _fetch_responders(self) -> None:
        """
        Start initialization response listener. Add respoder_ids from proper
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
                self.subs.append(data["responder_id"])

        subscriber.subscribe(**{"event-signal-response": _init_handler})
        self.init_listener = subscriber.run_in_thread()

    def _check_subs(self, event: str) -> Tuple[Any, List[int]]:
        """
        Listen for responses from all registered subscribers. Return
        listener, as well as value based on responders' RAS codes.
        """
        if not self.subs:
            return None, [0]

        to_check = set(self.subs)
        subscriber = self.redis.pubsub(ignore_subscribe_messages=True)
        result_code_holder = [ResultCodes.ALL_SUBS_SUCCESS]

        def _sub_handler(item: Dict) -> None:
            data = self._get_data_dict(item)
            if data and data["publisher_id"] == self.pub_id and data["event"] == event:
                if "ras" in data:
                    if data["responder_id"] not in to_check:
                        self.logger.warning(
                            f"Got a response from tool '{data['responder_id']}' but it's not on the known subscribers list (or already responded for '{event}'). RAS: {data['ras']}"
                        )
                    else:
                        to_check.remove(data["responder_id"])
                        if data["ras"] != 1:
                            self.logger.warning(
                                f"Tool '{data['responder_id']}' returned bad response for event '{event}', ras: {data['ras']}"
                            )
                            result_code_holder[0] = ResultCodes.SUB_FAILED
            if not to_check:
                listener.stop()

        subscriber.subscribe(**{"event-signal-response": _sub_handler})
        listener = subscriber.run_in_thread()
        return listener, result_code_holder

    def _valid_str_list(self, names: List[str]) -> bool:
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
        self,
        event: str,
        sample: int = -1,
        tag: str = None,
        metadata: Dict = None,
        timeout: int = 20,
    ) -> int:
        """
        Publish a legal event signal. Includes additional options to specify sample_no,
        a tag, and any other additional metadata. Will then wait for responses from
        subscribed responders (if any). The method will give up once the timeout period
        is reached (default = 20s). Returns one of the below result codes based on
        signal publish/response success.

        RESULT CODES:
        ALL_SUBS_SUCCESS = 0 = ALL SUBS RESPONDED WELL
        SUB_FAILED = 1 = ONE OR MORE SUB RESPONDED BADLY
        MISSING_RESPONE = 2 = NOT ALL SUBS RESPONDED
        """
        if not isinstance(timeout, int):
            raise TypeError("'timeout' arg must be an int value")

        skip_check = False
        if not self.init_listener or not self.init_listener.is_alive():
            self.logger.warning(
                "Exporter is not initialized, not accepting subscribers and no event checking"
            )
            skip_check = True

        if event == "initialization":
            raise ValueError(
                "Please use the 'initialize()' method for publishing 'initialization' signals"
            )

        if event == "shutdown":
            raise ValueError(
                "Please use the 'shutdown()' method for 'shutdown' signals"
            )

        if not skip_check and not event in self.legal_events:
            raise ValueError(
                f"Event {self.event} not one of legal events: {self.legal_events}"
            )

        sig = self._sig_builder(event=event, sample=sample, tag=tag, metadata=metadata)
        sub_check, result_code_holder = self._check_subs(event)

        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())
        self.logger.debug(f"Signal published for event {event}")

        counter = 0
        while sub_check and sub_check.is_alive():
            time.sleep(0.1)
            counter += 1
            if counter >= timeout * 10:
                self.logger.error(
                    f"Timeout after waiting {timeout} seconds for sub response"
                )
                sub_check.stop()
                return ResultCodes.MISSING_RESPONSE

        return result_code_holder[0]

    def initialize(
        self, legal_events: List[str], tag: str = None, expected_resps: List[str] = None
    ) -> None:
        """
        Publishes an initialization message. Starts a listener that reads responses
        to the initialization message and adds responders to the subscriber list.
        Sets list of legal event names for future signals, and also allows for optional
        input of expected responders (subscribers) as well as a tag.
        """
        if not self._valid_str_list(legal_events):
            raise TypeError("'legal_events' arg must be a list of string event names")

        if expected_resps:
            if not self._valid_str_list(expected_resps):
                raise TypeError(
                    "'expected_hosts' arg must be a list of string hostnames"
                )
            for resp in expected_resps:
                self.subs.append(resp)

        self.legal_events = legal_events
        sig = self._sig_builder(event="initialization", tag=tag)
        self._fetch_responders()
        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())
        self.logger.debug("Initialization successful!")

    def shutdown(self, tag: str = None) -> None:
        """
        Shuts down initialization response listener (stops accepting subscribers).
        Wipes the subscriber list and publishes a shutdown message.
        """
        sig = self._sig_builder(event="shutdown", tag=tag)
        self.init_listener.stop()
        self.subs = []
        self.redis.publish(channel="event-signal-pubsub", message=sig.to_json_str())
        self.logger.debug("Shutdown successful!")


class SignalResponder:
    """
    A signal management object for tools that wish to respond to event/state signals.
    Can be used both for listening for signals as well as responding to them. Also
    allows for locking onto specific tags/publisher_ids. Uses the standard signal
    response protocol for all published messages.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        responder_name: str = platform.node(),
        log_level="INFO",
    ) -> None:
        """
        Sets exporter object fields and generates unique responder_id.
        Allows for specification of redis host/port.
        """
        # self.logger: logging.Logger = logging.getLogger("SignalResponder").getChild(
        #    responder_name
        # )
        self.logger = _create_logger("SignalResponder", responder_name, log_level)
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.subscriber = self.redis.pubsub(ignore_subscribe_messages=True)
        self.subscriber.subscribe("event-signal-pubsub")
        self.responder_id = responder_name + "-" + str(uuid.uuid4()) + "-resp"
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
        response = Response(self.responder_id, publisher_id, event, ras)
        self.redis.publish("event-signal-response", response.to_json_str())
        self.logger.debug(f"Published response for event {event} from {publisher_id}")

    def lock_id(self, publisher_id: str) -> None:
        """
        Lock onto a specific publisher_id. Only receive signals from the
        chosen id.
        """
        if isinstance(publisher_id, str):
            self.locked_id == publisher_id
            self.logger.debug(f"Locked onto id: {publisher_id}")
        else:
            raise TypeError("Unsuccessful lock, 'publisher_id' must be type str")

    def lock_tag(self, tag: str) -> None:
        """
        Lock onto a specific tag. Only receive signals from the chosen tag.
        """
        if isinstance(tag, str):
            self.locked_tag == tag
            self.logger.debug(f"Locked onto tag: {tag}")
        else:
            raise TypeError("Unsuccessful lock, 'tag' must be type str")
