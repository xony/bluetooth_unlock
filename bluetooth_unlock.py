#!/usr/bin/env python
# encoding: utf-8

# This script periodically checks the RSSI value of a device specified in client_file.
# It does that by connecting bluetooth ACL and then does an authentication request.
# The device must be paired (through normal OS means) with the computer beforehand.
#
# lock_threshold  : if RSSI is smaller or equal to this value, then the computer will be locked
# unlock_threshold: if RSSI is larger or equal to this value, then the computer will be unlocked
# refresh_time    : script will sleep for this time before issuing another probe
#
#  NOTE: if the value is smaller than the unlock_threshold but larger than the lock_threshold for 3 times consecutively, then screen will be locked

import os
import sys
import time
import signal
import subprocess
import os
import sys
import struct
import bluetooth._bluetooth as bluez
import json
from config import *



# define the exception for command not completed
class CommandNotCompletedError(Exception):
    """Exception raised for Command Not Completed
    """

    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ConnectionExistsError(Exception):
    """Exception raised for non-existing connection 
    """

    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ConnectionTimedOut(Exception):
    """Exception raised for timed out connection 
    """

    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Timeout():
    """Timeout class using ALARM signal."""
    class Timeout(Exception):
        pass
 
    def __init__(self, sec):
        self.sec = sec
 
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.sec)
 
    def __exit__(self, *args):
        signal.alarm(0)    # disable alarm
 
    def raise_timeout(self, *args):
        raise Timeout.Timeout()

def execute_commands(cmds):
    if isinstance(cmds, basestring):
        tmpstr = userstr.split()
        tmpstr.append(cmds)
        subprocess.Popen(tmpstr, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    else:
        for cmd in cmds:
            tmpstr = userstr.split()
            tmpstr.append(cmd)
            subprocess.Popen(tmpstr, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

def printpacket(pkt):
    for c in pkt:
        sys.stdout.write("%02x " % struct.unpack("B",c)[0])
    print 

def save_filter(sock):
    # save current filter
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )
    return old_filter

def restore_filter(old_filter,sock):
    # restore old filter
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
    


def create_acl_conn(sock):
    # save current filter
    old_filter = save_filter(sock)
    
    ## packet structure: 6B -> BT ADDRESS, 2B -> DM1, 1B -> R1, 1B -> reserved 0x00, 2B -> Clock offset 0x0000, 1B -> Allow role switch 
    #cmd_pkt = struct.pack("BBBBBBBBBBBBB", 0x22, 0x22, 0xef, 0xbb, 0x48, 0x6f, 0x00, 0x08, 0x02, 0x00, 0x00, 0x00, 0x01)
    address = bluez.str2ba(device_address)
    cmd_pkt = struct.pack("6sBBBBBBB", address, 0x18, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01)
    bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_CREATE_CONN, cmd_pkt)

    results = []

    done = False
    while not done:
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_CONN_COMPLETE:
            done = True
            status, conn_id = struct.unpack("xBH", pkt[2:6])

            print "-" * 10
            printpacket(pkt)
            print conn_id, "status: ", status

            if status == 4:
                print "ACL page timed out"
                raise ConnectionTimedOut("ACL page timed out")
            elif status == 11:
                print "ACL connection already established!"
                raise ConnectionExistsError("ACL connection already established!")
            elif status == 0:
                print "connection successfully completed"
            elif status == 9:
                print "connection limit exceeded!"
                raise ConnectionExistsError("ACL connection limit exceeded! There must be a connection...")
            elif status == 34:
                print "link manager timed out..."
                raise ConnectionTimedOut("Link manager timed out")
            else:
                print "something funky happened, let us reset!"
                raise ConnectionExistsError("Unknown error, resetting")
            
        elif event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                printpacket(pkt)
                print "ACL connection failed"
                done = True
                raise CommandNotCompletedError("Connection could not be established")


    # restore old filter
    restore_filter(old_filter, sock)

    return conn_id 

def cancel_acl_conn(sock):
    os.system("hciconfig hci0 down")
    os.system("hciconfig hci0 up")

def cancel_acl_conn_old(sock):
    # save current filter
    old_filter = save_filter(sock)
    
    ## packet structure: 6B -> BT ADDRESS, 2B -> DM1, 1B -> R1, 1B -> reserved 0x00, 2B -> Clock offset 0x0000, 1B -> Allow role switch 
    address = bluez.str2ba(device_address)
    cmd_pkt = struct.pack("6s", address)
    bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, bluez.OCF_RESET)

    results = []

    done = False
    while not done:
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_CMD_COMPLETE:
            done = True
            status = struct.unpack("B", pkt[3])[0]

            print "-" * 10
            printpacket(pkt)
            print "status: ", status

            if status == 2:
                print "No connection requested"
            elif status == 11:
                print "ACL connection already established!"
            elif status == 0:
                print "connection cancel successfully completed"
            
        elif event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                print "ACL connection cancel failed"
                #printpacket(pkt[3:7])
                done = True
                raise CommandNotCompletedError("Connection could not be canceled")


    # restore old filter
    restore_filter(old_filter, sock)

def read_rssi(sock, handle):
    # save current filter
    old_filter = save_filter(sock) 
 
    cmd_pkt = struct.pack("H", handle)
    result = bluez.hci_send_cmd(sock, bluez.OGF_STATUS_PARAM, bluez.OCF_READ_RSSI, cmd_pkt) 


    done = False
    while not done:
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                print "RSSI command failed"
                done = True
                raise CommandNotCompletedError("RSSI could not be read")
        elif event == bluez.EVT_CMD_COMPLETE:
            status, returned_handle, rssi = struct.unpack("xBHb",pkt[5:])
            if status == 0 and returned_handle == handle:
                done = True
            elif status != 0 and returned_handle == handle:
                rssi = -255 # some error while reading the RSSI 
                done = True

    # restore old filter
    restore_filter(old_filter, sock)
    
    return rssi

def enable_authentication(sock):
    
    old_filter = save_filter(sock)
    
    bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, bluez.OCF_READ_AUTH_ENABLE) 
    
    done = False
    while not done:
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                done = True
                raise CommandNotCompletedError("Disconnect somehow failed")
        elif event == bluez.EVT_CMD_COMPLETE:
            status, auth_enabled = struct.unpack("BB",pkt[6:])
            if status == 0:
                done = True
            elif status != 0:
                raise CommandNotCompletedError("Authentication Mode could not be read!")

    
    cmd_pkt = struct.pack("B", 0x01)
    bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, bluez.OCF_WRITE_AUTH_ENABLE, cmd_pkt) 
    
    done = False
    while not done:
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                done = True
                raise CommandNotCompletedError("Authentication could not be forced")
        elif event == bluez.EVT_CMD_COMPLETE:
            done = True


    restore_filter(old_filter, sock)
    os.system("hciconfig hci0 sspmode 0") # disable simple pairing mode

def authenticate(sock, handle):
    
    old_filter = save_filter(sock)
    
    cmd_pkt = struct.pack("H", handle)
    bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_AUTH_REQUESTED, cmd_pkt) 
    
    done = False
    while not done:
        pkt = sock.recv(255)
        #printpacket(pkt)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                print "-" * 10
                printpacket(pkt)
                print "auth command failed"
                done = True
                raise CommandNotCompletedError("command failed")
        elif event == bluez.EVT_AUTH_COMPLETE:
            status, returned_handle = struct.unpack("xBH",pkt[2:])
            if status == 0 and handle == returned_handle:
                done = True
            elif status != 0 and handle == returned_handle:
                print "authenticatin failed! is device paired?"
		done = True
                raise CommandNotCompletedError("Authentication did not succeed!") 

    restore_filter(old_filter, sock)


def close_connection(sock, handle):
    
    old_filter = save_filter(sock)
    
    cmd_pkt = struct.pack("HB", handle, 0x15)
    result = bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_DISCONNECT, cmd_pkt) 
    
    done = False
    while not done:
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                print "-" * 10
                printpacket(pkt)
                print "disconnection command failed"
                done = True
                raise CommandNotCompletedError("Disconnect somehow failed")
        elif event == bluez.EVT_DISCONN_COMPLETE:
            done = True


    restore_filter(old_filter, sock)

def init_connection():
    dev_id = 0
    connection = -1
    try:
	sock = bluez.hci_open_dev(dev_id)
    except:
	print "error accessing bluetooth device..."
	sys.exit(1)
    return sock
    

def deinit_connection(sock, connection):
    try:
	close_connection(sock, connection)
    except (CommandNotCompletedError, bluez.error):
	print "Disconnecting failed!"



def main():
    global userstr
    global unlockstr
    global lockstr
    global client_file
    global lock_threshold
    global unlock_threshold
    global refresh_time
    global device_address

    # first we need to know the address of our unlocking device, load this from the client_file
    with open(client_file, 'r') as outfile:
        client_dict = json.load(outfile)
    
    if len(client_dict) != 1:
        sys.exit("Error: Currently this script needs exactly one device capable of unlocking.")
    
    for device_key in client_dict:
        device_address = client_dict[device_key]
    
    if not os.geteuid() == 0:
      sys.exit("Only root can run this script")
    
    system_unlocked = False
    os.system("rfkill unblock bluetooth")
    execute_commands(lockstr)
    negative_count = 0
    while True:
    
        sock = init_connection()
        try:
	    with Timeout(4):
            	connection_handle = create_acl_conn(sock)
        except (CommandNotCompletedError, ConnectionTimedOut, bluez.error):
            if system_unlocked == True:
                print "System locked"
                system_unlocked = False
                execute_commands(lockstr)
            time.sleep(refresh_time)
            continue
        except (ConnectionExistsError, Timeout.Timeout):
            if system_unlocked == True:
                print "System locked"
                system_unlocked = False
                execute_commands(lockstr)
            os.system("hcitool dc %s" % device_address)
            #time.sleep(refresh_time)
            print "resetting connection..."
            try:
                cancel_acl_conn(sock)
            except bluez.error:
                pass
            continue
    
        try:
	    with Timeout(4):
            	authenticate(sock, connection_handle)
    	    	current_rssi = read_rssi(sock, connection_handle)
        except (CommandNotCompletedError, bluez.error):
    	    if system_unlocked == True:
    	        print "System locked"
    	        system_unlocked = False
    	        execute_commands(lockstr)
    	    time.sleep(refresh_time)
            deinit_connection(sock, connection_handle)
    	    continue
   	except Timeout.Timeout:
            if system_unlocked == True:
                print "System locked"
                system_unlocked = False
                execute_commands(lockstr)
            os.system("hcitool dc %s" % device_address)
            #time.sleep(refresh_time)
            print "resetting connection..."
            try:
                cancel_acl_conn(sock)
            except bluez.error:
                pass
            continue
 
        
        if current_rssi <= lock_threshold and negative_count >= count_threshold and system_unlocked == True:
            print "System locked"
            system_unlocked = False
            execute_commands(lockstr)
        elif current_rssi >= unlock_threshold:
            negative_count = 0
            system_unlocked = True
            #print "System unlocked"
            execute_commands(unlockstr)
        elif current_rssi <= lock_threshold and system_unlocked == True and negative_count < count_threshold:
            negative_count += 1
        elif current_rssi > lock_threshold and current_rssi < unlock_threshold:
            negative_count = 0
        print "RSSI:", current_rssi 
        deinit_connection(sock, connection_handle)
        time.sleep(refresh_time)

main()
