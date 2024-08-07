#!/usr/bin/python3

# Using data from /data/sfng/ipmapping

import subprocess
import re
import time
import json

GEN10 = {
    "HPE Eth 10/25Gb 2P 641SFP28 Adptr" : "16.28.1002",
    "iLO 5" : "2.72 Sep 04 2022",
    "Redundant System ROM" : "v2.68 (07/14/2022)",
    "System ROM" : "v2.68 (07/14/2022)",
}

GEN10PLUS = {
     "Mellanox ConnectX-6 LX OCP3.0": "26.33.1048",
     "iLO 5" : "2.72 Sep 04 2022",
     "Redundant System ROM" : "U46 v1.64 (08/11/2022)",
     "System ROM" : "U46 v1.64 (08/11/2022)",
     "Nvidia Network Adapter" : "26.33.1048",
     "HPE MR216i-a Gen10+" : "52.16.3-4455",
}

GEN11 = {
     "iLO 6" : "1.53 Oct 10 2023",
     "Redundant System ROM" : "U54 v1.46 (09/26/2023)",
     "System ROM" : "U54 v1.46 (09/26/2023)",
     "HPE MR216i-o Gen11" : "52.24.3-4948",
     "Mellanox ConnectX-6 LX OCP3.0" : "26.37.1700",
     "Mellanox Network Adapter" : "26.37.1700",
     "Server Platform Services (SPS) Firmware" : "6.0.4.75.0",
     "HPE SN1610E 32Gb 2p FC HBA" : "14.2.589.5"
}

GEN11_2023_10 = {
     "iLO 6" : "1.56 Jan 27 2024",
     "Redundant System ROM" : "U54 v2.12 (12/13/2023)",
     "System ROM" : "U54 v2.12 (12/13/2023)",
     "HPE MR216i-o Gen11" : "52.24.3-4948",
     "Mellanox ConnectX-6 LX OCP3.0" : "26.37.1700",
     "Mellanox Network Adapter" : "26.37.1700",
     "Server Platform Services (SPS) Firmware" : "6.1.4.05.0",
     "HPE SN1610E 32Gb 2p FC HBA" : "14.2.589.5",
     "Intelligent Platform Abstraction Data" : "10.0.0 Build 47"
}


FW_FULL = "FW_full.txt"

FAILED_SERVERS = {}

def get_servers_info():
    servers = {}
    with open("/data/sfng/ipmapping", "r") as f:                                 
        for line in f:
            extracted = line.split("\t")
            extracted = [s for s in extracted if s != '']
            sn, ip, ul = extracted
            ul = ul.rstrip()
            print(f"Firmware check for server: UL: {ul}, SN: {sn}, IP: {ip}")
            servers[sn] = {}
            servers[sn]["IP"] = ip
            servers[sn]["UL"] = ul
    with open("/etc/ansible/hosts", "r") as f:
        for line in f:
            if "ILOCZ" in line:
                extracted = line.split("\t")
                extracted = [i for i in extracted if i != '']
                sn, ip, pswd = extracted
                servers[sn[3:]]["PSWD"] = pswd.split("=")[1]

    return servers


def get_ilocfg(serversi, params):
    print(f"Writing results of fw check into: {FW_FULL}")
    summary = {}

    with open(FW_FULL, "w") as file:
        for sn in servers.keys():
            print(f"{'-'*20}\nProcessing fw check for {sn}:")
            command  = f"ilorest serverinfo --firmware --url {servers[sn]['IP']} -u Administrator -p {servers[sn]['PSWD']}"
            print(command)
            ilocheck = subprocess.run([command], stdout=subprocess.PIPE, shell=True)
            serv_fw = ilocheck.stdout.decode('utf-8')
            file.write(f'{sn}: {servers[sn]["IP"]}  {servers[sn]["UL"]}\n')
            file.write(serv_fw)
            file.write(f"\n{'-'*40}\n")
            flag = 0

            datacollection = serv_fw.split("\n")
            for fw, vr in params.items():
                for data in datacollection:
                    if fw in data:
                        if vr not in data:
                            flag = 1
                            print('\033[91m' + f"FAIL: {data} != {vr}" '\033[0m')
                            if vr not in FAILED_SERVERS.keys():
                                FAILED_SERVERS[vr] = []    
                            if [sn, servers[sn]['IP']] not in FAILED_SERVERS[vr]:
                                FAILED_SERVERS[vr].append([sn, servers[sn]['IP']])
                        else:
                            print('\033[92m' + f"OK: {data} == {vr}" + '\033[0m')
                        if "Mellanox Network Adapter" in data:
                            name = data.split("-")[0]
                            version = data.split(":")[-1]
                            data = name + version
                        if data in summary.keys():
                            summary[data] += 1
                        else:
                            summary[data] = 1
            if flag == 0:
                print('\033[92m' + 'Everything is OK' + '\033[0m')
            
    for k, v in summary.items():
        print(f"{k}: {v}")

def count_disks():
    nvme = "NVMe Drive"
    sata = "960GB 6G SATA SSD"
    
    print(f"\n{'-'*40}\nCounting disks: ")    

    with open(FW_FULL, "r") as file:
        content = file.read()
        print(f"{nvme}: {content.count(nvme)}")        
        print(f"{sata}: {content.count(sata)}")        


if __name__ == '__main__':
    servers = get_servers_info()
    
    params = GEN10
    print("Input servers generation [1, 2, 3, 4]: ")
    print("1. Gen10 (default)\n2. Gen10PLUS \n3. Gen11\n4. Gen11 2023.10")
    
    user_input = input(">>")
    if user_input == "2":
        params = GEN10PLUS
    if user_input == "3":
        params = GEN11
    if user_input == "4":
        params = GEN11_2023_10

    get_ilocfg(servers, params)                                                          
    count_disks()
    
    for key, servers in FAILED_SERVERS.items():
        print(f"FAILED fw: {key}")
        for server in servers:
            print(server[0], server[1])
            
