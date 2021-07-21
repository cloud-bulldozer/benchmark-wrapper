from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
import redis
import random
import platform

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
                raise TypeError(f"The field {name} should be type {field_type}, not {type(self.__dict__[name])}")

        legal_events = [
            "initialization",
            "benchmark-start",
            "benchmark-stop",
            "sample-start",
            "sample-stop",
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
        return str(result)

class SignalExporter:
    def __init__(self, benchmark_name, redis_host="localhost", redis_port=6379) -> None:
        self.subs = []
        self.bench_name = benchmark_name
        self.bench_id = benchmark_name + datetime.now().strftime(f'%m%d%Y%H%M%Sr{random.randint(1000,9999)}')
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)

    def _fetch_responders(self):
        #Check for responses to initialization
        return []

    def _check_subs(self):
        #Check responses of subscribers
        return 0

    def publish_signal(self, event, runner_host=None, sample:int=-1, user=None) -> int:
        # NOTE: runner_host will be automatically populated w/ platform.node() if nothing is passed in
        
        #Unsure if necessary twice vvv
        legal_events = [
            "initialization",
            "benchmark-start",
            "benchmark-stop",
            "sample-start",
            "sample-stop",
        ]

        if not event in legal_events:
            print(f"Event {self.event} not one of legal events: {legal_events}")
            exit(1)
        #End of unecessary(?) ^^^

        sig = Signal(
            benchmark_id=self.bench_id,
            benchmark_name=self.bench_name,
            event=event
        )
        sig.runner_host = runner_host if runner_host else sig.runner_host
        sig.user = user if user else sig.user
        sig.sample_no = sample if sample >= 0 else sig.sample_no

        # publish
        self.redis.publish(channel="benchmark-signal-pubsub", message=sig.to_json_str())

        if event == "initialization":
            subscribers = self._fetch_responders()
            result = 3
            for sub in subscribers:
                self.subs.append(sub)
        else:
            result = self._check_subs()
        return result
