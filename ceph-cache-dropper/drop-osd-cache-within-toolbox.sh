#!/bin/bash

OK=0
NOTOK=1


osds=$(ceph osd tree | awk '/osd\./{print $4}')
if [ $? != $OK ] ; then
    exit $NOTOK
fi

for o in $osds ; do
    ceph tell $o cache drop || exit $NOTOK
done
