from signals import signal_exporter
import time
from multiprocessing import Process

responder = signal_exporter.SignalResponder()
def _listener():
    for signal in responder.listen():
        print(signal)
        responder.respond(signal["publisher_id"], signal["event"], 1)
init = Process(target=_listener)
init.start()

sig_ex = signal_exporter.SignalExporter("fakemark")
print("\nBENCHMARK INIT TEST\n")
sig_ex.initialize(legal_events=["benchmark-start", "benchmark-stop"])
time.sleep(1)
print("Proof of response (subs): " + str(sig_ex.subs))
time.sleep(1)

print("\nBENCHMARK START TEST\n")
result = sig_ex.publish_signal("benchmark-start", metadata={"something": "cool info"})
time.sleep(1)
print(f"SUBS CLEARED! Result code: {result}")
time.sleep(1)

print("\nBENCHMARK SHUTDOWN TEST\n")
print("Listening: " + str(sig_ex.init_listener.is_alive()))
sig_ex.shutdown()
time.sleep(1)
print("Listening: " + str(sig_ex.init_listener.is_alive()))
print("NO LONGER LISTENING, DONE")

init.terminate()
