#!/usr/bin/env python
# encoding: utf-8

# performs a device inquiry and then saves the device id with strongest RSSI to a json file

import os
import sys
import struct
import bluetooth._bluetooth as bluez
import json, argparse

client_file = "known_clients"

def printpacket(pkt):
    for c in pkt:
        sys.stdout.write("%02x " % struct.unpack("B",c)[0])
    print 


def device_inquiry_with_with_rssi(sock):
    # save current filter
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # perform a device inquiry on bluetooth device #0
    # The inquiry should last 8 * 1.28 = 10.24 seconds
    # before the inquiry is performed, bluez should flush its cache of
    # previously discovered devices
    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

    duration = 4
    max_responses = 255
    cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
    bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, cmd_pkt)

    results = []

    done = False
    while not done:
        pkt = sock.recv(255)
        print "packet: "
        printpacket(pkt)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_EXTENDED_INQUIRY_RESULT:
            pkt = pkt[3:]
            nrsp = struct.unpack("B", pkt[0])[0]
            for i in range(nrsp):
                addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
                rssi = struct.unpack("b", pkt[1+13*nrsp+i])[0]
                results.append( ( addr, rssi ) )
                print "[%s] RSSI: [%d]" % (addr, rssi)
        if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
            pkt = pkt[3:]
            nrsp = struct.unpack("B", pkt[0])[0]
            for i in range(nrsp):
                addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
                rssi = struct.unpack("b", pkt[1+13*nrsp+i])[0]
                results.append( ( addr, rssi ) )
                print "[%s] RSSI: [%d]" % (addr, rssi)
        elif event == bluez.EVT_INQUIRY_COMPLETE:
            done = True
        elif event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                print "uh oh..."
                printpacket(pkt[3:7])
                done = True
        elif event == bluez.EVT_INQUIRY_RESULT:
            pkt = pkt[3:]
            nrsp = struct.unpack("B", pkt[0])[0]
            for i in range(nrsp):
                addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
                results.append( ( addr, -1 ) )
                print "[%s] (no RRSI)" % addr
        else:
            print "unrecognized packet type 0x%02x" % ptype


    # restore old filter
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )

    return results


parser = argparse.ArgumentParser(description='Get the Bluetooth ID with strongest RSSI.')
parser.add_argument('name',help='name of the nearest device.')
args = parser.parse_args()

dev_id = 0
try:
    sock = bluez.hci_open_dev(dev_id)
except:
    print "error accessing bluetooth device..."
    sys.exit(1)


discovered_events = device_inquiry_with_with_rssi(sock)


if len(discovered_events) > 0:
    strongest_device, curr_max = discovered_events[0] 
    for (device, rssi) in discovered_events:
        if rssi > curr_max:
            strongest_device = device
            curr_max = rssi

    print "found device ", strongest_device, " with rssi ", rssi, " to be named: ", args.name
    #if not os.path.isfile(client_file):
        # just save our stuff to the client file
    with open(client_file, 'w') as outfile:
            outdict = {}
            outdict[args.name] = strongest_device
            print outdict
            json.dump(outdict, outfile)
    #else:
        # now open the file for reading and writing
        #with open(client_file, 'r') as outfile:
        #    outdict = json.load(outfile)
        #    outdict[args.name] = strongest_device
        #with open(client_file, 'w') as outfile:
        #    json.dump(outdict, outfile)
else:
    print "No discoverable device in vicinity!"
            
