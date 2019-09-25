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
import time
import subprocess
import sys
import json
import shutil
import os
import uuid
import base64

def _index_result(server,port):
    index = "stockpile-results-raw"
    es = elasticsearch.Elasticsearch([
        {'host': server,'port': port}],send_get_body_as='POST')
    if not es.indices.exists(index):
        es.indices.create(index=index)
    indexed=True
    my_uuid = str(uuid.uuid4())
    timestamp = time.gmtime()
    
    stockpile_file = os.popen('grep stockpile_output_path group_vars/all.yml | awk \'{printf $2}\'').read()
    kube_dir = os.popen('grep tmp_dir group_vars/all.yml | awk \'{printf $2}\'').read()

    if os.path.exists(stockpile_file):
        _upload_to_es(stockpile_file,my_uuid,timestamp,es,index)
    
    for payload_file in os.listdir(kube_dir):
        _upload_to_es(kube_dir+"/"+payload_file,my_uuid,timestamp,es,index)

    return my_uuid

def _upload_to_es(payload_file,my_uuid,timestamp,es,index):
    payload = open(payload_file, "rb").read()
    raw_stockpile = str(base64.urlsafe_b64encode(payload))
    try:
        _data = { "uuid": my_uuid,
                        "timestamp": timestamp,
                        "data": raw_stockpile }
        es.index(index=index, body=_data)
    except Exception as e:
        print(repr(e) + "occurred for the json document:")
        indexed=False

def _run_stockpile(directory):
    cwd = os.getcwd()
    os.chdir(directory)
    cmd = ["/usr/bin/ansible-playbook", "-i", "hosts", "stockpile.yml"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return process.returncode

def _dl_stockpile(directory,hosts,group,priv):
    cmd = ["git", "clone", "https://github.com/cloud-bulldozer/stockpile.git", directory]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = process.communicate()
    
    # Copy files into stockpile directory
    try:
      shutil.copy(hosts,directory+"/hosts")
    except IOError as e:
      print("Unable to copy file. %s" % e)
      sys.exit(1)
   
    try:
      shutil.copy(group,directory+"/group_vars/all.yml")
    except IOError as e:
      print("Unable to copy file. %s" % e)
      sys.exit(1)
   
    # If we should run privledged then remove comment marking from backpack_set.yaml 
    if priv.lower() == "yes":
      with open(directory+"/roles/backpack_kube/files/backpack_set.yaml", "r") as f:
        newText=f.read().replace('#', '')

      with open(directory+"/roles/backpack_kube/files/backpack_set.yaml", "w") as f:
        f.write(newText)

    return process.returncode

def main():
    parser = argparse.ArgumentParser(description="Stockpile Wrapper script")
    parser.add_argument(
        '-i', '--inventory',
        help='Provide hosts inventory file location')
    parser.add_argument(
        '-g', '--group',
        help='Provide group_vars/all.yml file location')
    parser.add_argument(
        '-d', '--directory',
        help='Provide temporary working directory')
    parser.add_argument(
        '-s', '--server',
        help='Provide elastic server information')
    parser.add_argument(
        '-p', '--port', 
        help='Provide elastic port information')
    parser.add_argument(
        '-u', '--use-privileges', 
        help='"yes" if the containers are allow to be privileged')
    args = parser.parse_args()
    _dl_stockpile(args.directory,args.inventory,args.group,args.use_privileges)
    _run_stockpile(args.directory)
    uuid = _index_result(args.server,args.port)
    print("uuid: ",uuid)

if __name__ == '__main__':
    sys.exit(main())
