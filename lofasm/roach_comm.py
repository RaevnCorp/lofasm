#library for functions that require talking to the ROACH Board

import corr
import os

#get ROACH ip from environment variable
try:
    roach_ip = os.environ['ROACH_IP']
except KeyError as err:
    print "ROACH_IP environment variable not set!"
    print "Defaulting to 192.168.4.21"
    roach_ip = '192.168.4.21'

#connect to roach board
fpga = corr.katcp_wrapper.FpgaClient(roach_ip)

def getRoachAccLen():
    return fpga.read_uint('acc_len')