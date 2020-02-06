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
import elasticsearch
import sys

def _check_index(server,port,uuid,index):
    _es_connection_string = str(server) + ':' + str(port)
    es = elasticsearch.Elasticsearch([_es_connection_string],send_get_body_as='POST')
    results = es.search(index=index, body={'query': {'term': {'uuid.keyword': uuid}}}, size=1)
    if results['hits']['total']['value'] > 0:
        return 0
    else:
        print("No result found in ES")
        return 1

def main():
    parser = argparse.ArgumentParser(description="Script to verify uploads to ES")
    parser.add_argument(
        '-s', '--server',
        help='Provide elastic server information')
    parser.add_argument(
        '-p', '--port',
        help='Provide elastic port information')
    parser.add_argument(
        '-u', '--uuid',
        help='UUID to provide to search')
    parser.add_argument(
        '-i', '--index',
        help='Index to provide to search')
    args = parser.parse_args()

    sys.exit(_check_index(args.server,args.port,args.uuid,args.index))


if __name__ == '__main__':
    sys.exit(main())
