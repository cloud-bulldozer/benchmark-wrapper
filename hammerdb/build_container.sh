#!/bin/bash
podman build --no-cache --tag=hammerdb .
podman run localhost/hammerdb
ID=$(podman ps --all | head -n 2 | grep -v CONTAINER | cut -d " " -f 1)
echo $ID
podman commit $ID quay.io/mkarg/hammerdb
podman push quay.io/mkarg/hammerdb:latest
