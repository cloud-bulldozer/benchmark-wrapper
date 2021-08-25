#  module to calculate filesystem statistics from statvfs info
#  in a form suitable for inclusion in Elasticsearch documents

import json
import os
import sys

bytes_per_GiB = 1024.0 * 1024.0 * 1024.0


def get_vfs_stat_dict(fspath):
    vfsinfo = os.statvfs(fspath)
    fsdict = {}
    # fsdict['bsize'] = vfsinfo.f_bsize
    # fsdict['frsize'] = vfsinfo.f_frsize
    # fsdict['blocks'] = vfsinfo.f_blocks
    # fsdict['bfree'] = vfsinfo.f_bfree
    # fsdict['bavail'] = vfsinfo.f_bavail
    # fsdict['files'] = vfsinfo.f_files
    # fsdict['ffree'] = vfsinfo.f_ffree
    # fsdict['favail'] = vfsinfo.f_favail
    #  note: bin only supported in python 3
    # fsdict['flag'] = bin(vfsinfo.f_flag)
    # fsdict['fsid'] = '0x%x' % vfsinfo.f_fsid
    fsdict["vfs-stat-path"] = fspath
    fsdict["GiB-blocks"] = vfsinfo.f_blocks * vfsinfo.f_bsize / bytes_per_GiB
    # simulates "df" output
    fsdict["pct-bytes-free"] = "%6.3f" % (100.0 * vfsinfo.f_bfree / vfsinfo.f_blocks)
    # simulates "df -i" output
    fsdict["pct-files-free"] = "%6.3f" % (100.0 * vfsinfo.f_ffree / vfsinfo.f_files)
    return fsdict


# unit test

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dirpath = sys.argv[1]
    else:
        dirpath = "."
    print(json.dumps(get_vfs_stat_dict(dirpath), indent=4))
