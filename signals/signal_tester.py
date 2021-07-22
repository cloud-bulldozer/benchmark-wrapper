from signals import signal_exporter
import redis
import json
import time
from threading import Thread

redis_con = redis.Redis(host="localhost", port=6379, db=0)
subscriber = redis_con.pubsub()
subscriber.subscribe("benchmark-signal-pubsub")

sig_ex = signal_exporter.SignalExporter("fakemark")
def _publish(event):
    sig_ex.publish_signal(event)

print("\nBENCHMARK INIT TEST\n")
init = Thread(target=_publish, args=("initialization",))
init.start()
time.sleep(0.1)

"""
for item in subscriber.listen():
    print(item)
    print(item['data'])
"""

subscriber.get_message()
message = subscriber.get_message()
data = json.loads(message["data"])
print(data)

bench_id = data["benchmark_id"]
event = data["event"]
response = {'benchmark_id':bench_id, 'tool_id':'testo_id', 'event':event}
redis_con.publish("benchmark-signal-response", json.dumps(response))
time.sleep(1)
print(sig_ex.subs)

print("\nBENCHMARK START TEST\n")
bstart = Thread(target=_publish, args=("benchmark-start",))
bstart.start()
time.sleep(0.1)
message = subscriber.get_message()
data = json.loads(message["data"])
print(data)
bench_id = data["benchmark_id"]
event = data["event"]
response = {'benchmark_id':bench_id, 'tool_id':'testo_id', 'event':event, 'ras':1}
redis_con.publish("benchmark-signal-response", json.dumps(response))
print("published")
time.sleep(0.5)
if not bstart.is_alive():
    print("CLEARED")
