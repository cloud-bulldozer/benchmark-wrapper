# vim: ft=make ts=4

.PHONY: smallfile build-smallfile push-smallfile test-smallfile clean-smallfile

SMALLFILE_IMAGE = ${REGISTRY_URL}/${ORG}/smallfile:${TAG}

smallfile: build-smallfile push-smallfile

build-smallfile:
	$(call build-container,${SMALLFILE_IMAGE},smallfile_wrapper/Dockerfile)

push-smallfile:
	$(call push-container,${SMALLFILE_IMAGE})

test-smallfile:
	smallfile_wrapper/ci_test.sh

clean-smallfile:
	${ENGINE} rmi ${SMALLFILE_IMAGE}
