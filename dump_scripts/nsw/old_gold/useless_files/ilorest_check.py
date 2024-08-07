#!/usr/bin/python3

# Using data from /data/sfng/ipmapping

import subprocess

with open("/data/sfng/ipmapping", "r") as f:
    for line in f:
        extracted = line.split("\t")
        extracted = [s for s in extracted if s != '']
        sn, ip, ul = extracted
        ul = ul.rstrip()
        print(f"Firmware check for server: UL: {ul}, SN: {sn}, IP: {ip}")
        command  = "ilorest serverinfo --firmware --url %s -u admin -p admin" % (ip) 
        ilocheck = subprocess.run([command], stdout=subprocess.PIPE, shell=True)
        serv_fw = ilocheck.stdout.decode('utf-8')
        print("Results:")
        print(serv_fw)
