# vim: ft=make ts=4

.PHONY: fs-drift build-fs-drift push-fs-drift test-fs-drift clean-fs-drift

FS_DRIFT_IMAGE = ${REGISTRY_URL}/${ORG}/fs-drift:${TAG}

snafu-fs-drift: build-fs-drift push-fs-drift

build-fs-drift: build-tmp/fs-drift

build-tmp/fs-drift: fs_drift_wrapper/* run_snafu.py
	$(call build-container,${FS_DRIFT_IMAGE},fs_drift_wrapper/Dockerfile,fs-drift)

push-fs-drift:
	$(call push-container,${FS_DRIFT_IMAGE})

test-fs-drift:
	fs_drift_wrapper/ci_test.sh

clean-fs-drift:
	${ENGINE} rmi ${FS_DRIFT_IMAGE}
