#!/usr/bin/env python
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

import argparse
from datetime import datetime
import elasticsearch
import subprocess
import sys
import json
from transcribe.render import transcribe

def _index_result(server,port,payload_file):
    index = "backpack-results"
    es = elasticsearch.Elasticsearch([
        {'host': server,'port': port}],send_get_body_as='POST')
    if not es.indices.exists(index):
        es.indices.create(index=index)
    es.indices.put_mapping(index=index, doc_type="result", body={"dynamic_templates": [{"rule1": {"mapping": {"type": "string"},"match_mapping_type": "long"}}]})
    indexed=True
    scribe_uuid = "NONE"
    for scribed in transcribe(payload_file,'stockpile'):
        try:
            scribe_module = json.loads(scribed)['module']
            es.index(index=scribe_module+"-metadata", doc_type="result", body=scribed)
            scribe_uuid = json.loads(scribed)['scribe_uuid']
        except Exception as e:
            print(repr(e) + "occurred for the json document:")
            print(str(scribed))
            indexed=False
    return scribe_uuid

def _run_backpack():
    cmd = ["/usr/bin/ansible-playbook", "-c", "local", "/opt/app-root/src/stockpile.yml"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return process.returncode


def main():
    parser = argparse.ArgumentParser(description="Backpack Wrapper script")
    parser.add_argument(
        '-f', '--file',
        help='Provide json file location')
    parser.add_argument(
        '-s', '--server',
        help='Provide elastic server information')
    parser.add_argument(
        '-p', '--port', 
        help='Provide elastic port information')
    args = parser.parse_args()
    _run_backpack()
    uuid = _index_result(args.server,args.port,args.file)
    print("uuid: ",uuid)

if __name__ == '__main__':
    sys.exit(main())
