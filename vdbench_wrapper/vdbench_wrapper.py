#!/usr/bin/env python3
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import logging
import requests
import tarfile

from vdbench_wrapper import trigger_vdbench

logger = logging.getLogger('snafu')

BASE_PATH = '/opt/vdbench'


class vdbench_wrapper():

    def __init__(self, parser):

        # collect arguments
        parser.add_argument(
            '-c', '--config',
            help='Provide configuration file')
        parser.add_argument(
            '-o', '--output',
            help='path to output files',
            default=BASE_PATH+'/outputs')
        parser.add_argument(
            '-s', '--samples',
            help='number of times to run benchmark, defaults to 1',
            type=int,
            default=1)
        parser.add_argument(
            '-l', '--log',
            help='log file (Full path)',
            default=BASE_PATH+'/logs')
        parser.add_argument(
            '-d', '--dir',
            help='all outputs Results.tar.gz file location',
            default='/tmp')
        self.args = parser.parse_args()

        self.args.cluster_name = 'mycluster'
        if 'clustername' in os.environ:
            self.args.cluster_name = os.environ['clustername']

        self.uuid = ''
        self.user = ''
        self.server = ''
        self.cache_drop_ip = ''

        if 'uuid' in os.environ:
            self.uuid = os.environ['uuid']
        if 'test_user' in os.environ:
            self.user = os.environ['test_user']
        if 'ceph_cache_drop_pod_ip' in os.environ:
            self.cache_drop_ip = os.environ['ceph_cache_drop_pod_ip']
        self.samples = self.args.samples
        self.output_dir = self.args.output
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if self.args.config is None:
            raise Exception('Configuration file did not given.')
        if self.args.config[0] == '/':
            self.config_file_path = self.args.config
        else:
            self.config_file_path = BASE_PATH + '/' + self.args.config
            self.args.config = self.config_file_path
        self.logs = self.args.log
        if not os.path.exists(self.logs):
            os.makedirs(self.logs)
        self.results_dir = self.args.dir
        self.all_results = self.results_dir + '/Results.tgz'

    # TODO: this can be moved to general utils
    def cache_drop(self):
        try:
            drop = requests.get(
                'http://{}:9432/drop_osd_caches'.format(self.cache_drop_ip)
            ).text
        except Exception:
            logger.error('Failed to send cache drop to {}'.format(
                self.cache_drop_ip)
            )
        if 'SUCCESS' in drop:
            logger.info('Ceph OSD cache successfully dropped')
        else:
            logger.error('Request to drop Ceph OSD cache failed')

    def run(self):

        """
            execute vdbench for X number of samples,
            yield the trigger_vdbench_generator.
        """
        for i in range(1, self.samples + 1):
            samples_dir = self.output_dir + '/' + str(i)
            if self.cache_drop_ip:
                logger.debug('Going to drop the OSDs cache before test.')
                self.cache_drop()
            else:
                logger.info('The OSDs cache did not drop before the test.')

            trigger_vdbench_generator = trigger_vdbench._trigger_vdbench(
                    self.args, samples_dir, self.user, self.uuid, i,
            )
            yield trigger_vdbench_generator

        # collect all results data to tar.gz file
        with tarfile.open('{}/Results.tgz'.format(
                self.results_dir), 'w:gz') as tar:
            tar.add(self.logs, arcname=self.logs)
            tar.add(self.output_dir, arcname=self.output_dir)
        tar.close()
        logger.info('All results can be found at : {}'.format(self.all_results))  # noqa
        logger.info('Test Run Finished')
