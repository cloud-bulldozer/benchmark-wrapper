FROM registry.access.redhat.com/ubi9:latest

RUN dnf install -y --nodocs python3-pip python3-devel gcc
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/

RUN curl -L https://software.intel.com/content/dam/develop/external/us/en/documents/l_onemklbench_p_2021.2.0_109.tgz --output linpack.tgz
RUN tar xzvf linpack.tgz -C /opt
