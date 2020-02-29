# vim: ft=make ts=4

.PHONY: fio build-fio push-fio test-fio clean-fio

FIO_IMAGE = ${REGISTRY_URL}/${ORG}/fio:${TAG}

snafu-fio: build-fio push-fio

build-fio: build-tmp/fio

build-tmp/fio: fio_wrapper/* run_snafu.py
	$(call build-container,${FIO_IMAGE},fio_wrapper/Dockerfile,fio)

push-fio:
	$(call push-container,${FIO_IMAGE})

test-fio:
	fio_wrapper/ci_test.sh

clean-fio:
	${ENGINE} rmi ${FIO_IMAGE}
