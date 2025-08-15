FROM registry.access.redhat.com/ubi9:latest

RUN dnf install -y --nodocs python3 python3-pip python3-devel jq gcc && dnf clean all
RUN dnf install -y --nodocs redis && dnf clean all
RUN curl -L https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz | tar xz -C /usr/bin/ oc
RUN curl -L $(curl -s https://api.github.com/repos/openshift/rosa/releases/latest | jq -r ".assets[] | select(.name == \"rosa-linux-amd64\") | .browser_download_url") --output /usr/bin/rosa
RUN curl -L $(curl -s https://api.github.com/repos/openshift-online/ocm-cli/releases/latest | jq -r ".assets[] | select(.name == \"ocm-linux-amd64\") | .browser_download_url") --output /usr/bin/ocm
RUN chmod +x /usr/bin/rosa && chmod +x /usr/bin/ocm
RUN mkdir -p /.config/ocm
RUN chmod 777 /.config/ocm
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
