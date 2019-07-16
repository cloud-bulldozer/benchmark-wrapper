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

import elasticsearch

def index_result(es,workload,payload,_type="result"):
    es = elasticsearch.Elasticsearch([
        {'host': es['server'],'port': es['port'] }],send_get_body_as='POST')
    for result in payload:
         es.index(index="ripsaw_{}_{}".format(index,_type), body=result)
