# vim: ft=make ts=4

.PHONY: sysbench build-sysbench push-sysbench test-sysbench clean-sysbench

SYSBENCH_IMAGE = ${REGISTRY_URL}/${ORG}/sysbench:${TAG}

sysbench: build-sysbench push-sysbench

build-sysbench:
	$(call build-container,${SYSBENCH_IMAGE},sysbench/Dockerfile)

push-sysbench:
	$(call push-container,${SYSBENCH_IMAGE})

test-sysbench:
	sysbench/ci_test.sh

clean-sysbench:
	${ENGINE} rmi ${SYSBENCH_IMAGE}
