from signals import signal_exporter
import time
from multiprocessing import Process

responder = signal_exporter.SignalResponder(responder_name="fakeresp")
def _listener():
    for signal in responder.listen():
        print(signal)
        if "tag" in signal and signal["tag"] == "bad":
            ras = 0
        else:
            ras = 1
        responder.respond(signal["publisher_id"], signal["event"], ras)
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

print("\nBENCHMARK STOP TEST\n")
result = sig_ex.publish_signal("benchmark-stop", metadata={"tool": "give bad resp"}, tag="bad")
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
