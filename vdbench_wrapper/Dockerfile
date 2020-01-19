FROM registry.access.redhat.com/ubi8:latest

USER root
RUN dnf install --nodocs -y python3 python3-pip python3-numpy java
RUN dnf clean all

RUN pip3 install --user elasticsearch configparser statistics XlsxWriter requests
RUN pip3 install --upgrade-strategy=only-if-needed pyyaml "elasticsearch>=6.0.0,<=7.0.2"

RUN ln -s /usr/bin/python3 /usr/bin/python

RUN  mkdir -p /mnt/pvc/ /opt/snafu/
RUN for i in `seq 0 9` ; do mkdir /mnt/lun$i ; done
COPY vdbench/.bashrc /root/
COPY . /opt/snafu/

WORKDIR /opt/snafu
CMD ["/bin/bash"]
