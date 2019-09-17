FROM centos/tools
USER root
RUN rpm -iv https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y python2-pip
RUN pip install --upgrade pip
RUN pip install elasticsearch configparser statistics numpy scipy redis
RUN mkdir -pv /opt/snafu
COPY * /opt/snafu/
RUN git clone https://github.com/parallel-fs-utils/fs-drift /opt/fs-drift
RUN ln -sv /opt/fs-drift/fs-drift.py /usr/local/bin/
RUN ln -sv /opt/fs-drift/rsptime_stats.py /usr/local/bin/
