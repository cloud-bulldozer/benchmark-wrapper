# vim: ft=make ts=4

.PHONY: hammerdb build-hammerdb push-hammerdb test-hammerdb clean-hammerdb

HAMMERDB_IMAGE = ${REGISTRY_URL}/${ORG}/hammerdb:${TAG}

snafu-hammerdb: build-hammerdb push-hammerdb

build-hammerdb: build-tmp/hammerdb

build-tmp/hammerdb: hammerdb/* run_snafu.py
	$(call build-container,${HAMMERDB_IMAGE},hammerdb/Dockerfile,hammerdb)

push-hammerdb:
	$(call push-container,${HAMMERDB_IMAGE})

test-hammerdb:
	hammerdb/ci_test.sh

clean-hammerdb:
	${ENGINE} rmi ${HAMMERDB_IMAGE}
