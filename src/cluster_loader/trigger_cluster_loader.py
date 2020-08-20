import json
import os
import re
import subprocess

import yaml


class _trigger_cluster_loader:
    """
        Will execute with the provided arguments and return normalized results for indexing
    """

    def __init__(self, logger, cluster_name, result_dir, user, uuid, sample, path_binary,
                 test_name, console_cl_output):
        self.logger = logger
        self.result_dir = result_dir
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.cluster_name = cluster_name
        self.path_binary = path_binary
        self.test_name = test_name
        self.console_cl_output = console_cl_output

    def emit_actions(self):
        """
        Executes test and calls document parsers, if index_data is true will yield normalized data
        """
        execution_output_file = os.path.join(self.result_dir, 'cl_output.txt')
        file_stdout = open(execution_output_file, "w")
        cmd = [str(self.path_binary), 'run-test',
               '"[Feature:Performance][Serial][Slow] Load cluster should load the cluster [Suite:openshift]"'
               ]
        command_string = ""
        for _string in cmd:
            command_string = command_string + ' ' + _string
        self.logger.info('from current directory %s' % os.getcwd())
        try:
            if bool(self.console_cl_output) is True:
                command_string = command_string + ' | tee -a ' + str(execution_output_file)
                self.logger.info('running:' + str(command_string))
                process = subprocess.check_call(command_string, shell=True)
            else:
                self.logger.info('running:' + str(command_string))
                process = subprocess.check_call(command_string, stdout=file_stdout, shell=True)  # noqa
        except Exception as e:
            self.logger.exception(e)
            exit(1)
        self.logger.info("completed sample {} , results in {}".format(
            self.sample, execution_output_file))
        file_stdout.close()
        with open(str(execution_output_file)) as f:
            output_file_content = f.readlines()
        pattern = re.compile('^{.*}')
        match_list = list(filter(pattern.match, output_file_content))
        if not match_list:
            self.logger.error("Clusterloader exited without completing")
            exit(1)
        cl_output_json = match_list[0].strip()
        cl_output_dict = json.loads(cl_output_json)
        self.logger.info("cl output is {}".format(
            cl_output_json))
        config_file_location = ""
        if "VIPERCONFIG" in os.environ:
            config_file_location = os.environ["VIPERCONFIG"]
        if config_file_location == "":
            pattern = re.compile('.*INFO: Using config ')
            config_file_location = \
                list(filter(pattern.match, output_file_content))[0].strip().split(
                    'INFO: Using config ', 1)[1].replace('"', '')
        self.logger.info("config file location is {}".format(
            config_file_location))
        with open(config_file_location, 'r') as stream:
            try:
                config_dict = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.logger.info("configuration is {}".format(
            config_dict))
        output_template = {}
        output_template['config'] = config_dict['ClusterLoader']
        output_template['provider'] = config_dict['provider']
        output_template['cluster_name'] = self.cluster_name
        output_template['uuid'] = self.uuid
        output_template['user'] = self.user
        output_template['sample'] = self.sample
        output_template['test_name'] = self.test_name
        output_template.update(cl_output_dict)
        yield output_template, 'cl'
