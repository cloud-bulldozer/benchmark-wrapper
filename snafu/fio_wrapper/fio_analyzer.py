import statistics
import time


class Fio_Analyzer:
    """
    Fio Analyzer - this class will consume processed fio json results and calculate the average
    total iops for x number of samples.results are analyzed based on operation and io size,
    this is a static evaluation and future enhancements could evalute results based on
    other properties dynamically.
    """

    def __init__(self, uuid, user, cluster_name):
        self.uuid = uuid
        self.user = user
        self.fio_processed_results_list = []
        self.sample_list = []
        self.operation_list = []
        self.io_size_list = []
        self.sumdoc = {}
        self.cluster_name = cluster_name

    def add_fio_result_documents(self, document_list, starttime):
        """
        for each new document add it to the results list with its starttime
        """
        for document in document_list:
            fio_result = {}
            fio_result["document"] = document
            fio_result["starttime"] = starttime
            self.fio_processed_results_list.append(fio_result)

    def calculate_iops_sum(self):
        """
        will loop through all documents and will populate parameter lists and sum
        total iops across all host for a specific operation and io size
        """

        for fio_result in self.fio_processed_results_list:
            if fio_result["document"]["fio"]["jobname"] != "All clients":
                sample = fio_result["document"]["sample"]

                if fio_result["document"]["global_options"].get("bs"):
                    bs_value = fio_result["document"]["global_options"]["bs"]
                elif fio_result["document"]["global_options"].get("bsrange"):
                    bs_value = fio_result["document"]["global_options"]["bsrange"]

                rw = fio_result["document"]["fio"]["job options"]["rw"]

                if sample not in self.sample_list:
                    self.sample_list.append(sample)
                if rw not in self.operation_list:
                    self.operation_list.append(rw)
                if bs_value not in self.io_size_list:
                    self.io_size_list.append(bs_value)

        for sample in self.sample_list:
            self.sumdoc[sample] = {}
            for rw in self.operation_list:
                self.sumdoc[sample][rw] = {}
                for bs_value in self.io_size_list:
                    self.sumdoc[sample][rw][bs_value] = {}

            # get measurements

        for fio_result in self.fio_processed_results_list:
            if fio_result["document"]["fio"]["jobname"] != "All clients":
                sample = fio_result["document"]["sample"]

                if fio_result["document"]["global_options"].get("bs"):
                    bs_value = fio_result["document"]["global_options"]["bs"]
                elif fio_result["document"]["global_options"].get("bsrange"):
                    bs_value = fio_result["document"]["global_options"]["bsrange"]

                rw = fio_result["document"]["fio"]["job options"]["rw"]

                if not self.sumdoc[sample][rw][bs_value]:
                    time_s = fio_result["starttime"] / 1000.0
                    self.sumdoc[sample][rw][bs_value]["date"] = time.strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time_s)
                    )
                    self.sumdoc[sample][rw][bs_value]["write"] = 0
                    self.sumdoc[sample][rw][bs_value]["read"] = 0

                self.sumdoc[sample][rw][bs_value]["write"] += float(
                    fio_result["document"]["fio"]["write"]["iops"]
                )
                self.sumdoc[sample][rw][bs_value]["read"] += float(
                    fio_result["document"]["fio"]["read"]["iops"]
                )

    def emit_actions(self):
        """
        Will calculate the average iops across multiple samples and return list containing items
        for each result based on operation/io size
        """

        importdoc = {"ceph_benchmark_test": {"test_data": {}}, "uuid": self.uuid, "user": self.user}

        self.calculate_iops_sum()

        for oper in self.operation_list:
            for io_size in self.io_size_list:
                average_write_result_list = []
                average_read_result_list = []
                tmp_doc = {}
                tmp_doc["object_size"] = io_size  # set document's object size
                tmp_doc["operation"] = oper  # set documents operation
                firstrecord = True
                calcuate_percent_std_dev = False

                for itera in self.sample_list:  #
                    average_write_result_list.append(self.sumdoc[itera][oper][io_size]["write"])
                    average_read_result_list.append(self.sumdoc[itera][oper][io_size]["read"])

                    if firstrecord:
                        importdoc["date"] = self.sumdoc[itera][oper][io_size]["date"]
                        firstrecord = True

                read_average = sum(average_read_result_list) / len(average_read_result_list)
                if read_average > 0.0:
                    tmp_doc["read-iops"] = read_average
                    if len(average_read_result_list) > 1:
                        calcuate_percent_std_dev = True
                else:
                    tmp_doc["read-iops"] = 0

                write_average = sum(average_write_result_list) / len(average_write_result_list)
                if write_average > 0.0:
                    tmp_doc["write-iops"] = write_average
                    if len(average_write_result_list) > 1:
                        calcuate_percent_std_dev = True
                else:
                    tmp_doc["write-iops"] = 0

                tmp_doc["total-iops"] = tmp_doc["write-iops"] + tmp_doc["read-iops"]

                if calcuate_percent_std_dev:
                    if "read" in oper:
                        tmp_doc["std-dev-%s" % io_size] = round(
                            ((statistics.stdev(average_read_result_list) / read_average) * 100), 3
                        )
                    elif "write" in oper:
                        tmp_doc["std-dev-%s" % io_size] = round(
                            ((statistics.stdev(average_write_result_list) / write_average) * 100), 3
                        )
                    elif "randrw" in oper:
                        tmp_doc["std-dev-%s" % io_size] = round(
                            (
                                (
                                    (
                                        statistics.stdev(average_read_result_list)
                                        + statistics.stdev(average_write_result_list)
                                    )
                                    / tmp_doc["total-iops"]
                                )
                                * 100
                            ),
                            3,
                        )

                importdoc["ceph_benchmark_test"]["test_data"] = tmp_doc
                importdoc["cluster_name"] = self.cluster_name
                # TODO add ID to document
                index = "analyzed-result"
                yield importdoc, index
