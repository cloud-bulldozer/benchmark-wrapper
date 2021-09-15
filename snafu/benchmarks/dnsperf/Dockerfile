FROM registry.centos.org/centos:8

RUN dnf -y install --nodocs \
        epel-release \
        openssl-devel \
        python38 \
        yum-plugin-copr
RUN dnf -y install --nodocs ck-devel
RUN dnf -y copr enable @dnsoarc/dnsperf
RUN dnf -y install dnsperf
RUN dnf clean all
RUN rm --force --recursive /var/cache/yum && \
    ln --symbolic /usr/bin/python3 /usr/bin/python && \
    mkdir --parent /opt/snafu/snafu

COPY . /opt/snafu
RUN python -m pip install --editable /opt/snafu
WORKDIR /opt/snafu
