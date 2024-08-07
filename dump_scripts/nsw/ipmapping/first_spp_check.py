#!/usr/bin/python3

import subprocess

print("Checking servers after spp:")

ls_spp = subprocess.run(["ls /data/log/NokiaNSW | grep ilorest"], stdout=subprocess.PIPE, shell=True)
spp_passed = ls_spp.stdout.decode('utf-8')

hosts = subprocess.run(["cat /etc/ansible/hosts | grep CZ"], stdout=subprocess.PIPE, shell=True)
hosts_info = hosts.stdout.decode('utf-8').split("\n")

srvrs = {}

for line in hosts_info:
    extracted = line.split("\t")
    extracted = [s for s in extracted if s != ""]
    if len(line) > 30:
        sn, ip, psw = extracted
        sn = sn[3:]
        ip  = ip.rstrip()
        srvrs[sn] = ip + "\t" + psw

servers_count = len(srvrs)
fail_count = 0

with open("uloc.txt", "r") as servers:
    for server in servers:
        sn, uloc = server.split("\t")
        if sn not in spp_passed:
            print("\n" + f"{sn}" + '\033[93m' + "  NOT PASSED" + '\033[0m')
            print(f"SN: {sn} {uloc}  {srvrs[sn]}")
            fail_count += 1        
        else:
            print(f"{sn}" + '\033[92m' + "  PASSED" + '\033[0m') 

print('\033[94m' + f"Passed: {servers_count - fail_count} servers from {servers_count}" + '\033[0m')

