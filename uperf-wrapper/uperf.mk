# vim: ft=make ts=4

.PHONY: uperf build-uperf push-uperf test-uperf clean-uperf

UPERF_IMAGE = ${REGISTRY_URL}/${ORG}/uperf:${TAG}

snafu-uperf: build-uperf push-uperf

build-uperf: build-tmp/uperf

build-tmp/uperf: uperf-wrapper/* run_snafu.py
	$(call build-container,${UPERF_IMAGE},uperf-wrapper/Dockerfile,uperf)

push-uperf:
	$(call push-container,${UPERF_IMAGE})

test-uperf:
	uperf-wrapper/ci_test.sh

clean-uperf:
	${ENGINE} rmi ${UPERF_IMAGE}
