#!/bin/sh

if [ "$#" -ne 4 ]; then
  echo "ERROR : Expected 4 args"
  echo "Usage: ./linpack.sh LINPACK_TESTS PROBLEM_SIZES LEADING_DIMENSIONS RERUN"
  exit 1
fi

# Location of Linpack binary
LINPACK='/opt/benchmarks_2021.2.0/linux/mkl/benchmarks/linpack/xlinpack_xeon64'

LINPACK_DAT='/tmp/linpack.dat'

NUM_CPU=`cat /proc/cpuinfo | grep processor | wc -l`
export OMP_NUM_THREADS=$NUM_CPU

LINPACK_TESTS=$1
PROBLEM_SIZES=$2
LEADING_DIMENSIONS=$3
RERUN=$4

echo "Sample Intel(R) LINPACK data file (from lininput_xeon64)" > ${LINPACK_DAT}
echo "Intel(R) LINPACK data" >> ${LINPACK_DAT}
echo "$LINPACK_TESTS # number of tests" >> ${LINPACK_DAT}
echo "$PROBLEM_SIZES # problem sizes" >> ${LINPACK_DAT}
echo "$LEADING_DIMENSIONS # leading dimensions" >> ${LINPACK_DAT}
echo "$RERUN # times to run a test " >> ${LINPACK_DAT}
echo "4 # alignment values (in KBytes)" >> ${LINPACK_DAT}

${LINPACK} < ${LINPACK_DAT}
