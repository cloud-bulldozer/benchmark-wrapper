#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the uperf benchmark. See http://uperf.org/ for more information."""
from typing import Dict, Iterable, List, Tuple, Union
import re
import datetime
from snafu.wrapper import Benchmark, JSONMetric


class Uperf(Benchmark):
    """
    Wrapper for the uperf benchmark.
    """

    tool_name = "uperf"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arg_group.add_argument(
            "-w", "--workload", dest="workload", env_var="WORKLOAD", help="Provide XML workload location"
        )
        self.arg_group.add_argument(
            "-s",
            "--sample",
            dest="sample",
            env_var="SAMPLE",
            default=1,
            type=int,
            help="Number of times to run the benchmark",
        )
        self.arg_group.add_argument(
            "--resourcetype",
            dest="kind",
            env_var="RESOURCETYPE",
            help="Provide the resource type for uperf run - pod/vm/baremetal",
        )
        # TODO: need help text for these and add some standardization
        self.arg_group.add_argument("--ips", dest="client_ips", env_var="ips", default="")
        self.arg_group.add_argument("-h", "--remoteip", dest="remote_ip", env_var="h", default="")
        self.arg_group.add_argument("--hostnet", dest="hostnetwork", env_var="hostnet", default="False")
        self.arg_group.add_argument("--serviceip", dest="service_ip", env_var="serviceip", default="False")
        self.arg_group.add_argument("--server-node", dest="server_node", env_var="server_node", default="")
        self.arg_group.add_argument("--client-node", dest="client_node", env_var="client_node", default="")
        self.arg_group.add_argument("--cluster-name", dest="cluster_name", env_var="clustername", default="")
        self.arg_group.add_argument("--num-pairs", dest="num_pairs", env_var="num_pairs", default="")
        self.arg_group.add_argument(
            "--multus-client", dest="multus_client", env_var="multus_client", default=""
        )
        self.arg_group.add_argument(
            "--network-policy", dest="networkpolicy", env_var="networkpolicy", default=""
        )
        self.arg_group.add_argument("--nodes-count", dest="nodes_in_iter", env_var="node_count", default="")
        self.arg_group.add_argument("--pod-density", dest="density", env_var="pod_count", default="")
        self.arg_group.add_argument("--colocate", dest="colocate", env_var="colocate", default="")
        self.arg_group.add_argument("--step-size", dest="step_size", env_var="stepsize", default="")
        # density_range and node_range are defined and exported in the cr file
        # it will appear in ES as startvalue-endvalue, for example
        # 5-10, for a run that began with 5 nodes involved and ended with 10
        self.arg_group.add_argument(
            "--density-range", dest="density_range", env_var="density_range", default=""
        )
        self.arg_group.add_argument("--node-range", dest="node_range", env_var="node_range", default="")
        # each node will run with density number of pods, this is the 0 based
        # number of that pod, useful for displaying throughput of each density
        self.arg_group.add_argument("--pod-id", dest="pod-id", env_var="my_pod_idx", default="")
        # TODO: Are these two common metadata?
        self.arg_group.add_argument("-u", "--uuid", dest="uuid", env_var="UUID", help="Provide UUID of run")
        self.arg_group.add_argument("--user", dest="user", env_var="USER", help="Provide user")

        self.required_args.update({"workload", "sample", "kind", "uuid", "user"})

    def preflight_checks(self) -> bool:
        checks = [self.check_required_args(), self.check_file(self.config.workload)]

        return False not in checks

    def run(self) -> Tuple[bool, List[str]]:
        """
        Run uperf benchmark ``self.config.sample`` number of times.

        Returns immediately if a sample fails. Will attempt to Uperf run three times for each sample.

        Returns
        -------
        tuple :
            First value in tuple is bool representing if we were able to run uperf successfully. Second
            value in tuple is a list of stdouts returned by successful uperf samples.
        """

        cmd = f"uperf -v -a -R -i 1 -m {self.config.workload}"
        results: List[str] = list()
        for sample_num in range(1, self.config.sample + 1):
            self.logger.info(f"Starting Uperf sample number {sample_num}")
            sample = self.run_process(cmd, retries=2, expected_rc=0)
            if not sample["success"]:
                self.logger.critical(f"Uperf failed to run! Got results: {sample}")
                return False, results
            else:
                self.logger.info(f"Finished collecting sample {sample_num}")
                self.logger.debug(f"Got results: {sample}")
                results.append(sample["stdout"])

        self.logger.info(f"Successfully collected {self.config.sample} samples.")
        return True, results

    @staticmethod
    def parse_stdout(stdout: str) -> Tuple[List[Tuple[str, str, str]], Dict[str, Union[str, int]]]:
        """Return parsed stdout of Uperf sample."""

        # This will effectivly give us:
        # <profile name="{{test}}-{{proto}}-{{wsize}}-{{rsize}}-{{nthr}}">
        config = re.findall(r"running profile:(.*) \.\.\.", stdout)[0]
        test_type, protocol, wsize, rsize, nthr = config.split("-")
        # This will yeild us this structure :
        #     timestamp, number of bytes, number of operations
        # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
        results = re.findall(r"timestamp_ms:(.*) name:Txn2 nr_bytes:(.*) nr_ops:(.*)", stdout)
        # We assume message_size=write_message_size to prevent breaking dependant implementations
        return (
            results,
            {
                "test_type": test_type,
                "protocol": protocol,
                "message_size": int(wsize),
                "read_message_size": int(rsize),
                "num_threads": int(nthr),
                "duration": len(results),
            },
        )

    def get_metrics(self, stdout: str, sample_num: int) -> List[JSONMetric]:
        """Return list of JSON-compatible dict metrics given Uperf sample."""

        results, data = self.parse_stdout(stdout)

        processed: List[JSONMetric] = []
        prev_bytes: int = 0
        prev_ops: int = 0
        prev_timestamp: float = 0.0
        bytes: int = 0
        ops: int = 0
        timestamp: float = 0.0
        norm_ops: int = 0
        norm_ltcy: float = 0.0

        for result in results:
            timestamp, bytes, ops = float(result[0]), int(result[1]), int(result[2])

            norm_ops = ops - prev_ops
            if norm_ops == 0:
                norm_ltcy = 0.0
            else:
                norm_ltcy = ((timestamp - prev_timestamp) / norm_ops) * 1000

            datapoint = {
                "workload": "uperf",
                "iteration": sample_num,
                "uperf_ts": datetime.datetime.fromtimestamp(int(result[0].split(".")[0]) / 1000),
                "bytes": bytes,
                "norm_byte": bytes - prev_bytes,
                "ops": ops,
                "norm_ops": norm_ops,
                "norm_ltcy": norm_ltcy,
                "density_range": [int(x) for x in self.config.density_range.split("-") if x != ""],
                "node_range": [int(x) for x in self.config.node_range.split("-") if x != ""],
            }
            config_keys = set(self.metadata).union(
                {
                    "uuid",
                    "user",
                    "cluster_name",
                    "hostnetwork",
                    "remote_ip",
                    "client_ips",
                    "service_ip",
                    "kind",
                    "client_node",
                    "server_node",
                    "num_pairs",
                    "multus_client",
                    "networkpolicy",
                    "density",
                    "nodes_in_iter",
                    "step_size",
                    "colocate",
                    "pod_id",
                }
            )
            for key in config_keys:
                datapoint[key] = getattr(self.config, key, None)
            datapoint.update(data)
            processed.append(JSONMetric(datapoint))
            prev_timestamp, prev_bytes, prev_ops = timestamp, bytes, ops

        return processed

    def emit_metrics(self, raw_results: List[str]) -> Iterable[JSONMetric]:
        """
        Emit uperf metrics.

        Takes in raw stdout samples from uperf. Essentially, take second value returned from ``run`` method
        and provide it here.
        """

        for sample_num, sample in enumerate(raw_results):
            for metric in self.get_metrics(sample, sample_num):
                yield metric
