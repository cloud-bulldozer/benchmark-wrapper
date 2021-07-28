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
sig_ex.publish_signal("benchmark-start", metadata={"something": "cool info"})
time.sleep(1)
print("SUBS CLEARED")
time.sleep(1)

print("\nBENCHMARK SHUTDOWN TEST\n")
sig_ex.shutdown()
time.sleep(1)
print("NO LONGER LISTENING, DONE")

init.terminate()