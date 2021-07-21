from signals import signal_exporter
import redis

redis_con = redis.Redis(host="localhost", port=6379, db=0)
subscriber = redis_con.pubsub()
subscriber.subscribe("benchmark-signal-pubsub")

sig_ex = signal_exporter.SignalExporter("fakemark")
sig_ex.publish_signal("initialization")

"""
for item in subscriber.listen():
    print(item)
    print(item['data'])
"""
subscriber.get_message()
message = subscriber.get_message()
print(message["data"])