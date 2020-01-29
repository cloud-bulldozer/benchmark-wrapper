FROM docker-registry.upshift.redhat.com/vdbench/vdbench:master

RUN dnf install --nodocs -y python3-numpy

RUN pip3 install --user elasticsearch configparser statistics requests
RUN pip3 install --upgrade-strategy=only-if-needed pyyaml "elasticsearch>=6.0.0,<=7.0.2"

RUN  mkdir -p /opt/snafu/
COPY . /opt/snafu/

WORKDIR /opt/snafu
