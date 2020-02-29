# vim: ft=make ts=4

.PHONY: all build test clean help

BASE_PROJECT = snafu
SHELL = /bin/bash
REGISTRY_URL = quay.io
ORG = rsevilla
REGISTRY = ${REGISTRY_URL}/${ORG}
TAG = latest
BENCHMARKS = fio fs-drift hammerdb iperf pgbench smallfile sysbench uperf ycsb 

ifeq (${SUDO},yes)
	ENGINE = sudo podman
else
	ENGINE = podman
endif

# Ensure we're using the latest base image
BUILD_FLAGS = --pull-always
BUILD = ${ENGINE} build ${BUILD_FLAGS}
PUSH = ${ENGINE} push

all: build push

# Include all makefiles
include */*.mk

build: build-fio build-fs-drift build-hammerdb build-iperf build-pgbench build-smallfile build-sysbench build-uperf build-ycsb
push: push-fio push-fs-drift push-hammerdb push-iperf push-pgbench push-smallfile push-sysbench push-uperf push-ycsb

define build-container
	@echo Building ${1}
	mkdir -p build-tmp
	${BUILD} --tag=${1} -f ${2} --iidfile build-tmp/${3} .
endef

define push-container
	@echo Pushing ${1}
	${PUSH} ${1}
endef

test:
	ci/run_ci.sh

clean: clean-fio clean-fs-drift clean-hammerdb clean-iperf clean-pgbench clean-smallfile clean-sysbench clean-uperf clean-ycsb

help:
	@echo -e "Targets for ${BASE_PROJECT}:\n"
	@echo "    make                   Build and push all container images."
	@echo "    make build             Build all container images."
	@echo "    make push              Push all container images."
	@echo "    make clean             Clean all container images."
	@echo "    make test              Perform CI tests."
	@echo "    make snafu-BENCHMARK   Build and push BENCHMARK container image."
	@echo "    make build-BENCHMARK   Build BENCHMARK container image."
	@echo "    make push-BENCHMARK    Build BENCHMARK container image."
	@echo "    make test-BENCHMARK    Execute BENCHMARK tests."
	@echo "    make clean-BENCHMARK   Clean BENCHMARK container image."
	@echo "    make help              Show this message."
	@echo -e "\nWhere BENCHMARK may be: ${BENCHMARKS}" 

