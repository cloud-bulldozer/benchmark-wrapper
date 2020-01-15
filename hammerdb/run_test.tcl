#!/usr/bin/tclsh
proc runtimer { seconds } {
set x 0
set timerstop 0
while {!$timerstop} {
  incr x
  after 1000
    if { ![ expr {$x % 60} ] } {
    set y [ expr $x / 60 ]
    puts "Time: $y minutes elapsed"
    }
  update
  if { [ vucomplete ] || $x eq $seconds } { set timerstop 1 }
     }
  return
}

puts "SETTING CONFIGURATION"
dbset db mssqls
dbset bm TPC-C
diset connection mssqls_server 192.168.42.214
diset connection mssqls_linux_server 192.168.42.214
diset connection mssqls_port 30159
diset connection mssqls_uid SA
diset connection mssqls_pass s3curePasswordString
diset connection mssqls_tcp true
diset tpcc mssqls_count_ware 1
diset tpcc mssqls_num_vu 1

puts "SETTING BENCHMARK OPTIONS"
diset tpcc mssqls_driver timed
diset tpcc mssqls_rampup 1
diset tpcc mssqls_duration 2
vuset logtotemp 1

loadscript
puts "SEQUENCE STARTED"
foreach z { 1 2 4 } {
puts "$z VU TEST"
vuset vu $z
vucreate 
vurun
runtimer 200
vudestroy
after 100000
}
puts "SEQUENCE COMPLETE"

