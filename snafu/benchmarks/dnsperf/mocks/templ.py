from pathlib import Path
from ttp import ttp
import dateutil.parser

import dataclasses


from snafu.benchmarks.dnsperf.dnsperf import DnsRttSample, DnsperfStdout, ThroughputSample

from pprint import pprint

with Path(__file__).with_name("dnsperf-template.xml").open() as template_f:
    output_template = template_f.read()


def parse_data(data):
    return {
        "throughput_ts": [ThroughputSample(**x) for x in data if "throughput" in x],
        "rtt_samples": [DnsRttSample(**y) for y in data if "throughput" not in y],
    }


def parse(stdout, output_template) -> DnsperfStdout:
    """Parse string output from the dnsperf benchmark."""

    output_parser = ttp(data=stdout, template=output_template)
    output_parser.parse()
    result = output_parser.result()[0][0]
    result["config"]["start_time"] = dateutil.parser.parse(result["config"]["start_time"])

    return DnsperfStdout(**result["stats"], **result["config"], **parse_data(result["data"]))


def parse_file(filename):
    with Path(__file__).with_name(filename).open() as data_f:
        data = data_f.read()
    return parse(data, output_template)


def main():
    stdout = parse_file("small-v-timeouts.txt")
    pprint(dataclasses.asdict(stdout))
    # pprint(data)


if __name__ == "__main__":
    main()
