# vim: ft=make ts=4

.PHONY: uperf build-uperf push-uperf test-uperf clean-uperf

UPERF_IMAGE = ${REGISTRY_URL}/${ORG}/uperf:${TAG}

uperf: build-uperf push-uperf

build-uperf:
	$(call build-container,${UPERF_IMAGE},uperf-wrapper/Dockerfile)

push-uperf:
	$(call push-container,${UPERF_IMAGE})

test-uperf:
	uperf-wrapper/ci_test.sh

clean-uperf:
	${ENGINE} rmi ${UPERF_IMAGE}
