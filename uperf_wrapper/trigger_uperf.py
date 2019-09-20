
from datetime import datetime
import numpy
import re
import subprocess

import logging

logger = logging.getLogger("snafu")

class trigger_uperf():
    def __init__(self, args):
        self.workload = args.workload[0]
        self.run = args.run[0]

        self.uuid = ""
        self.user = ""
        self.clientips = ""
        self.remoteip = ""
        self.hostnetwork = ""
        self.serviceip = ""
        self.cluster_name = args.cluster_name

    def _json_payload(self, data,iteration,uuid,user,hostnetwork,serviceip,remote,client,clustername):
        processed = []
        prev_bytes = 0
        prev_ops = 0
        for result in data['results'] :
            processed.append({
                "workload" : "uperf",
                "uuid": uuid,
                "user": user,
                "cluster_name": clustername,
                "hostnetwork": hostnetwork,
                "iteration" : int(iteration),
                "remote_ip": remote,
                "client_ips" : client,
                "uperf_ts" : datetime.fromtimestamp(int(result[0].split('.')[0])/1000),
                "test_type": data['test'],
                "protocol": data['protocol'],
                "service_ip": serviceip,
                "message_size": int(data['message_size']),
                "num_threads": int(data['num_threads']),
                "duration": len(data['results']),
                "bytes": int(result[1]),
                "norm_byte": int(result[1])-prev_bytes,
                "ops": int(result[2]),
                "norm_ops": int(result[2])-prev_ops
            })
            prev_bytes = int(result[1])
            prev_ops = int(result[2])
        return processed
    
    def _run_uperf(self, workload):
        cmd = "uperf -v -a -x -i 1 -m {}".format(workload)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        stdout,stderr = process.communicate()
        return stdout.strip(), process.returncode
    
    def _parse_stdout(self, stdout):
        # This will effectivly give us:
        # ripsaw-test-stream-udp-16384
        config = re.findall(r"running profile:(.*) \.\.\.",stdout)
        test = re.split("-",config[0])[0]
        protocol = re.split("-",config[0])[1]
        size = re.split("-",config[0])[2]
        nthr = re.split("-",config[0])[3]
        # This will yeild us this structure :
        #     timestamp, number of bytes, number of operations
        # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
        results = re.findall(r"timestamp_ms:(.*) name:Txn2 nr_bytes:(.*) nr_ops:(.*)",stdout)
        return { "test": test, "protocol": protocol, "message_size": size, "num_threads": nthr, "results" : results }
    
    def _summarize_data(self, data):
    
        byte = []
        op = []
        np = numpy
    
        for entry in data :
            byte.append(entry["norm_byte"])
            op.append(entry["norm_ops"])
    
        byte_result = np.array(byte)
        op_result = np.array(op)
    
        data = data[0]
        logger.info("+{} UPerf Results {}+".format("-"*(50), "-"*(50)))
        logger.info("Run : {}".format(data['iteration']))
        logger.info("Uperf Setup")
        logger.info("""
              hostnetwork : {}
              client: {}
              server: {}""".format(data['hostnetwork'],
                                   data['client_ips'],
                                   data['remote_ip']))
        logger.info("")
        logger.info("UPerf results for :")
        logger.info("""
              test_type: {}
              protocol: {}
              message_size: {}
              num_threads: {}""".format(data['test_type'],
                                         data['protocol'],
                                         data['message_size'],
                                         data['num_threads']))
        logger.info("")
        logger.info("UPerf results (bytes/sec):")
        logger.info("""
              min: {}
              max: {}
              median: {}
              average: {}
              95th: {}""".format(np.amin(byte_result),
                                 np.amax(byte_result),
                                 np.median(byte_result),
                                 np.average(byte_result),
                                 np.percentile(byte_result, 95)))
        logger.info("")
        logger.info("UPerf results (ops/sec):")
        logger.info("""
              min: {}
              max: {}
              median: {}
              average: {}
              95th: {}""".format(np.amin(op_result),
                                 np.amax(op_result),
                                 np.median(op_result),
                                 np.average(op_result),
                                 np.percentile(op_result, 95)))
        logger.info("+{}+".format("-"*(115)))
        
    def emit_actions(self):
        
        stdout = self._run_uperf(self.workload)
        
        if stdout[1] == 1 :
            logger.error("UPerf failed to execute, trying one more time..")
            stdout = self._run_uperf(self.workload)
            if stdout[1] == 1:
                logger.error("UPerf failed to execute a second time, stopping...")
                exit(1)
                
        data = self._parse_stdout(stdout[0])
        documents = self._json_payload(data,
                                       self.run,
                                       self.uuid,
                                       self.user,
                                       self.hostnetwork,
                                       self.serviceip,
                                       self.remoteip,
                                       self.clientips,
                                       self.cluster_name)
        
        logger.info(stdout[0])
        
        if len(documents) > 0 :
            #_index_result(server,port,documents)
            index = "-results"
            for document in documents:
                yield document, index
                
            self._summarize_data(documents)
