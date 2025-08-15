FROM quay.io/centos/centos:stream9 as builder
RUN dnf install -y make gcc libaio libaio-devel zlib-devel kernel-headers
RUN curl -L https://github.com/axboe/fio/archive/fio-3.36.tar.gz | tar xzf -
RUN pushd fio-fio-3.36 && ./configure --disable-native && make -j2

FROM quay.io/centos/centos:stream9 as runner
COPY --from=builder /fio-fio-3.36/fio /usr/local/bin/fio
RUN dnf install -y --nodocs git python3.11 python3.11-pip libaio zlib procps-ng iproute net-tools ethtool nmap iputils python3.11-devel gcc && dnf clean all
RUN ln -s /usr/bin/python3.11 /usr/bin/python
COPY . /opt/snafu
RUN pip3.11 install --upgrade pip
RUN pip3.11 install -e /opt/snafu/
