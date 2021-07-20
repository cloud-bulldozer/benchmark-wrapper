from dataclasses import dataclass
from typing import Any, Dict
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

    def to_jsonable(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("__") and k.endswith("__"))
        }
        return result
