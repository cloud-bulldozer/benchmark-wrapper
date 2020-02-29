# vim: ft=make ts=4

.PHONY: iperf build-iperf push-iperf test-iperf clean-iperf

IPERF_IMAGE = ${REGISTRY_URL}/${ORG}/iperf3:${TAG}

snafu-iperf: build-iperf push-iperf

build-iperf: build-tmp/iperf

build-tmp/iperf: iperf/* run_snafu.py
	$(call build-container,${IPERF_IMAGE},iperf/Dockerfile,iperf)

push-iperf:
	$(call push-container,${IPERF_IMAGE})

test-iperf:
	iperf/ci_test.sh

clean-iperf:
	${ENGINE} rmi ${IPERF_IMAGE}
