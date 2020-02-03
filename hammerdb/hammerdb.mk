# vim: ft=make ts=4

.PHONY: hammerdb build-hammerdb push-hammerdb test-hammerdb clean-hammerdb

HAMMERDB_IMAGE = ${REGISTRY_URL}/${ORG}/hammerdb:${TAG}

hammerdb: build-hammerdb push-hammerdb

build-hammerdb:
	$(call build-container,${HAMMERDB_IMAGE},hammerdb/Dockerfile)

push-hammerdb:
	$(call push-container,${HAMMERDB_IMAGE})

test-hammerdb:
	hammerdb/ci_test.sh

clean-hammerdb:
	${ENGINE} rmi ${HAMMERDB_IMAGE}
