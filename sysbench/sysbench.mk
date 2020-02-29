# vim: ft=make ts=4

.PHONY: sysbench build-sysbench push-sysbench test-sysbench clean-sysbench

SYSBENCH_IMAGE = ${REGISTRY_URL}/${ORG}/sysbench:${TAG}

snafu-sysbench: build-sysbench push-sysbench

build-sysbench: build-tmp/sysbench

build-tmp/sysbench: sysbench/* run_snafu.py
	$(call build-container,${SYSBENCH_IMAGE},sysbench/Dockerfile,sysbench)

push-sysbench:
	$(call push-container,${SYSBENCH_IMAGE})

test-sysbench:
	sysbench/ci_test.sh

clean-sysbench:
	${ENGINE} rmi ${SYSBENCH_IMAGE}
