# vim: ft=make ts=4

.PHONY: pgbench build-pgbench push-pgbench test-pgbench clean-pgbench

PGBENCH_IMAGE = ${REGISTRY_URL}/${ORG}/pgbench:${TAG}

pgbench: build-pgbench push-pgbench

build-pgbench:
	$(call build-container,${PGBENCH_IMAGE},pgbench-wrapper/Dockerfile)

push-pgbench:
	$(call push-container,${PGBENCH_IMAGE})

test-pgbench:
	pgbench-wrapper/ci_test.sh

clean-pgbench:
	${ENGINE} rmi ${PGBENCH_IMAGE}
