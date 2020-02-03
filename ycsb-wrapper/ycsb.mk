# vim: ft=make ts=4

.PHONY: ycsb build-ycsb push-ycsb test-ycsb clean-ycsb

YCSB_IMAGE = ${REGISTRY_URL}/${ORG}/ycsb-server:${TAG}

ycsb: build-ycsb push-ycsb

build-ycsb:
	$(call build-container,${YCSB_IMAGE},ycsb-wrapper/Dockerfile)

push-ycsb:
	$(call push-container,${YCSB_IMAGE})

test-ycsb:
	ycsb-wrapper/ci_test.sh

clean-ycsb:
	${ENGINE} rmi ${YCSB_IMAGE}
