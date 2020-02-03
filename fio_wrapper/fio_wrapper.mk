# vim: ft=make ts=4

.PHONY: fio build-fio push-fio test-fio clean-fio

FIO_IMAGE = ${REGISTRY_URL}/${ORG}/fio:${TAG}

fio: build-fio push-fio

build-fio: tmp/fio-id

tmp/fio-id: fio_wrapper
	$(call build-container,${FIO_IMAGE},fio_wrapper/Dockerfile)
	touch tmp/fio-id

push-fio:
	$(call push-container,${FIO_IMAGE})

test-fio:
	fio_wrapper/ci_test.sh

clean-fio:
	${ENGINE} rmi ${FIO_IMAGE}
