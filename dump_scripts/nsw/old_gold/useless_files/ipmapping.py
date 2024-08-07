#!/usr/bin/python3

import subprocess

subprocess.run(["systemctl", "restart", "dhcpd.service"])

result = subprocess.run(["dhcp-lease-list | grep ILO | awk '{print $2,$3}'"], stdout=subprocess.PIPE, shell=True)
out1 = result.stdout.decode('utf-8')

output = out1.split("\n")
servers = {}

for i in output:
    res = i.split(" ")
    if(len(res) == 2):
        ip = res[0]
        sn = res[1]
        servers[sn[3:]]=ip

result = []
with open("uloc.txt", "r") as file:
    for line in file:
        if(len(line) > 9):
            s_data = line.split("\t")
            sn = s_data[0];
            ul = s_data[1].rstrip();
            if sn in servers.keys():
                result.append(f'{sn}\t{servers[sn]}\t{ul}')
            else:
                print(f"Can't find {line} in dhcp-lease-list")
                exit(1)

for i in result:
    print(i)

 
