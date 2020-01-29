FROM registry.access.redhat.com/ubi8:latest

RUN curl -L https://github.com/brianfrankcooper/YCSB/releases/download/0.15.0/ycsb-0.15.0.tar.gz | tar xzf -
RUN mv ycsb-0.15.0 ycsb
RUN dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
RUN dnf install -y git java python3 python2 python3-pip python3-numpy
RUN pip3 install --upgrade-strategy=only-if-needed pyyaml "elasticsearch>=6.0.0,<=7.0.2"
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
