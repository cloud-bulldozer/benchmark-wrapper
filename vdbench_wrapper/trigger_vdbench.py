#!/usr/bin/env python3

from datetime import datetime
import subprocess
import time
import logging
import os
import sys

logger = logging.getLogger('snafu')


class _trigger_vdbench:
    """
        Will execute vdbench with the provided arguments and return
        normalized results for indexing
    """

    def __init__(self, args, working_dir, user, uuid, sample):
        self.working_dir = working_dir
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.cluster_name = args.cluster_name
        self.output_dir = args.output
        self.config_file_path = args.config
        self.logs = args.log
        self.results_dir = args.dir

    """
        Read the output file, and create clean and summarized results
         in JSON format
    """
    def _clean_output(self, vdbench_output_file):
        clean_output = {}
        clean_output['jobs'] = []
        clean_output['earliest_starttime'] = 0

        start_section = 0
        with open(vdbench_output_file, 'r') as fh:
            line = fh.readline()
            while line:
                line = line.strip('\n')

                # Summarized files/dirs/data for all clients.
                if 'Estimated totals for all' in line:
                    fdata = line.split(':')
                    clean_output['totla_clients'] = fdata[2].split()[5]
                    clean_output['total_dirs'] = fdata[4].split(';')[0]
                    clean_output['total_files'] = fdata[5].split(';')[0]
                    clean_output['total_data'] = fdata[6]

                # Individual information from client : files/dirs/data
                if 'Anchor size:' in line:
                    adata = line.split(':')
                    clean_output['dir_num'] = adata[5].split(';')[0].strip()
                    clean_output['files_num'] = adata[6].split(';')[0].strip()
                    clean_output['data_size'] = adata[7].strip().split(' ')[0]

                # start the test results section with header
                if 'Interval' in line and start_section == 1:
                    start_section = 2

                    # Starting of workload section
                    if 'starting_date' not in clean_output[rd]:
                        m = line.split()[0]
                        m = time.strptime(m, '%b').tm_mon

                        d = line.split()[1]
                        d = int(d.replace(',', ''))

                        y = int(line.split()[2])

                        h = int(clean_output[rd]['starting_time'].split(':')[0])  # noqa
                        mn = int(clean_output[rd]['starting_time'].split(':')[1])  # noqa
                        clean_output[rd]['starting_date'] = str(d) + '/' + str(m) + '/' + str(y)  # noqa

                        clean_output[rd]['timestamp'] = datetime(
                            y, m, d, h, mn).timestamp()
                        if clean_output['earliest_starttime'] < clean_output[rd]['timestamp']:  # noqa
                            clean_output['earliest_starttime'] = clean_output[rd]['timestamp']  # noqa
                    line = fh.readline()  # read the second line header.

                # Getting test results
                if ':' in line and start_section > 0 and 'Reached' not in line and 'anchor' not in line:  # noqa

                    dataline = line.split()

                    # Endinf of workload section
                    if 'avg' in line:
                        clean_output[rd]['iops']['read'] = dataline[7]
                        clean_output[rd]['iops']['write'] = dataline[9]
                        clean_output[rd]['iops']['total'] = dataline[2]

                        clean_output[rd]['bw']['read'] = dataline[11]
                        clean_output[rd]['bw']['write'] = dataline[12]
                        clean_output[rd]['bw']['total'] = dataline[13]

                        clean_output[rd]['lat']['read'] = dataline[8]
                        clean_output[rd]['lat']['write'] = dataline[10]
                        clean_output[rd]['lat']['total'] = dataline[3]

                        clean_output[rd]['bs'] = dataline[14]
                        clean_output[rd]['rdpct'] = dataline[6]

                # Getting the test (workload) name (RD) from the log
                if 'Starting RD' in line:
                    rd = line.split(';')[0].split('=')[-1]
                    starting_time = line.split()[0].split('.')[0]
                    clean_output['jobs'].append(rd)
                    clean_output[rd] = {
                        'iops': {'read': 0, 'write': 0, 'total': 0},
                        'bw': {'read': 0, 'write': 0, 'total': 0},
                        'lat': {'read': 0, 'write': 0, 'total': 0},
                        'bs': 0, 'rdpct': 0,
                        'starting_time': starting_time
                    }

                    if 'format' not in line:
                        clean_output[rd]['iorate'] = line.split(';')[2].split()[0].split('=')[-1].capitalize()  # noqa
                    else:
                        clean_output[rd]['iorate'] = 'Max'

                    start_section = 1

                if 'Vdbench distribution' in line:
                    clean_output['vdbench_version'] = line.split()[2].strip()

                line = fh.readline()

        fh.close()
        return clean_output

    def _run_vdbenchd(self):
        BASE_PATH = '/opt/vdbench/'
        cmd = [BASE_PATH, '-f', '-o']
        cmd[0] = BASE_PATH + 'bin/vdbench'
        cmd[1] = '-f ' + self.config_file_path
        cmd[2] = '-o ' + self.output_dir + '/' + str(self.sample)
        logger.debug(cmd)
        stdout = ''
        log_file = self.logs + '/' + str(self.sample) + '.log'
        olog = open(log_file, 'w')
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.logs
        )
        test_finished_ok = 0
        for line in process.stdout:
            line = line.decode('utf-8')  # decode the line from the process output  # noqa
            sys.stdout.write(line)  # write the line to STDOUT
            olog.write(line)  # write the line to the log file
            stdout += line  # add the line to the output results parameter.
            if 'Vdbench execution completed successfully' in line:
                test_finished_ok = 1
        process.wait()
        olog.close()
        if test_finished_ok:
            logger.info('Creating Excel report for {}'.format(log_file))
            os.system('{}scripts/make_report.py {}'.format(BASE_PATH, log_file))
        else:
            process.returncode = 1
        return stdout.strip(), process.returncode

    def emit_actions(self):
        """
        Executes vdbench test and calls document parsers,
        if index_data is true will yield normalized data
        """
        stdout = self._run_vdbenchd()
        vdbench_output_file = self.logs + '/' + str(self.sample) + '.log'
        if stdout[1] != 0:
            logger.error('vdbench failed to execute, trying one more time..')
            stdout = self._run_vdbenchd()
            if stdout[1] != 0:
                logger.error('vdbench failed to execute a second time, stopping...')  # noqa
                logger.error(stdout)
                exit(1)

        clean_stdout = self._clean_output(vdbench_output_file)
        logger.info('vdbench has successfully finished sample {} executing \
                     and results are in the dir {}\n'.format(
                        self.sample,  self.logs))
        logger.info(clean_stdout)

        vdbench_version = clean_stdout['vdbench_version']
        logger.info('vdbench version is : {}'.format(vdbench_version))

        index = 'results'
        yield clean_stdout, index
