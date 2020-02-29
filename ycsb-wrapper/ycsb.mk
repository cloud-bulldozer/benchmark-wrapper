# vim: ft=make ts=4

.PHONY: ycsb build-ycsb push-ycsb test-ycsb clean-ycsb

YCSB_IMAGE = ${REGISTRY_URL}/${ORG}/ycsb-server:${TAG}

snafu-ycsb: build-ycsb push-ycsb

build-ycsb: build-tmp/ycsb

build-tmp/ycsb: ycsb-wrapper/* run_snafu.py
	$(call build-container,${YCSB_IMAGE},ycsb-wrapper/Dockerfile,ycsb)

push-ycsb:
	$(call push-container,${YCSB_IMAGE})

test-ycsb:
	ycsb-wrapper/ci_test.sh

clean-ycsb:
	${ENGINE} rmi ${YCSB_IMAGE}
