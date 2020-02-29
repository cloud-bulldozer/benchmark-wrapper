# vim: ft=make ts=4

.PHONY: pgbench build-pgbench push-pgbench test-pgbench clean-pgbench

PGBENCH_IMAGE = ${REGISTRY_URL}/${ORG}/pgbench:${TAG}

snafu-pgbench: build-pgbench push-pgbench

build-pgbench: build-tmp/pgbench

build-tmp/pgbench: pgbench-wrapper/* run_snafu.py
	$(call build-container,${PGBENCH_IMAGE},pgbench-wrapper/Dockerfile,pgbench)

push-pgbench:
	$(call push-container,${PGBENCH_IMAGE})

test-pgbench:
	pgbench-wrapper/ci_test.sh

clean-pgbench:
	${ENGINE} rmi ${PGBENCH_IMAGE}
