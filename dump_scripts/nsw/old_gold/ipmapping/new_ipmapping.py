#!/usr/bin/python3

import os
import subprocess
import json
import requests

LO = ''

def getServers():

    ulocServers = {}
    with open("uloc.txt", "r") as file:
        for line in file:
            s_data = line.split("\t")
            sn = s_data[0]
            uloc = s_data[1].rstrip()
            ulocServers[sn] = uloc
    
    subprocess.run(["systemctl", "restart", "dhcpd.service"])

    result = subprocess.run(["dhcp-lease-list | grep ILO | awk '{print $2,$3}'"], stdout=subprocess.PIPE, shell=True)
    out1 = result.stdout.decode('utf-8')
    output = out1.split("\n")
    ipServers = {}
    
    for i in output:
        res = i.split(" ")
        if(len(res) == 2):
            ip = res[0]
            sn = res[1][3:]
            ipServers[sn]= ip
    
    servers = {} 
    for key in ulocServers.keys():
        if key not in ipServers.keys():
            print(f"Can't find {key} in dhcp-lease-list\n")
            exit(1)
        else:
            servers[key] = {}
            servers[key]["UL"] = ulocServers[key]
            servers[key]["IP"] = ipServers[key]
    
    for key, value in servers.items():
        print(f"{key}->{value}")    
 
    return servers

def getPasswd(servers):
    for key in servers.keys():
        print(f"Retrieving data for {key}")
        request = requests.get(f"https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER={key}")
        if request.status_code == 200:
            tmp = json.loads(request.text)
            
            lo = tmp["DATA"]["LEGACY_ORDER"]
            global LO
            if LO == '':
                LO = lo
            if lo != LO:
                print(f"SN: {key} have different LO:{lo} than previous servers: {LO}")
                exit(1)
                
            pswd = tmp["DATA"]["ILO_PASSWORD"]
            if len(pswd) != 8:
                print("Something wrong with password!")
                print(f"Check pswd: {pswd} for SN:{key}")
            else:
                servers[key]["PSWD"] = pswd 
        else:
            print("Cannot GET data from FX")
            exit(1)
    
    for key, value in servers.items():
        print(f"{key}->{value}")    

def writeIpmapping(servers):
    IPMAPPING = "/data/sfng/ipmapping"
    print(f"Writing servers data to {IPMAPPING}")
    with open(IPMAPPING, "w") as file:
        for key in servers.keys():
            print(f'{key}\t{servers[key]["IP"]}\t{servers[key]["UL"]}\n')
            file.write(f'{key}\t{servers[key]["IP"]}\t{servers[key]["UL"]}\n')

def writeHosts(servers):
    ANSIBLE_HOSTS = "/etc/ansible/hosts"
    print(f"Writing servers data to {ANSIBLE_HOSTS}")
    prepCmd = f"cp /etc/ansible/nokia.ori {ANSIBLE_HOSTS}"
    os.system(prepCmd)

    with open(ANSIBLE_HOSTS, "a") as file:
        for key in servers:
            print(f'ILO{key}\tbaseuri={servers[key]["IP"]}\tpassword={servers[key]["PSWD"]}\n')
            file.write(f'ILO{key}\tbaseuri={servers[key]["IP"]}\tpassword={servers[key]["PSWD"]}\n')

#not tested yet
#checks for ilocommunicatio through ilorest get request
def powerState(servers):
    username = "Administrator"

    for key in servers.keys():
        tmp = os.system(f'ilorest get PowerState --selector=ComputerSystem. --url {servers[key]["IP"]} -u {username} -p {servers[key]["PSWD"]} |  grep PowerState') 
        if tmp != 0:
            print("Failed ilorest request, check ilo for:")
            print(f'{key}:\tservers[key]["IP"]\t{username}\tservers[key]["PSWD"]')


def ansibleLogs():
    print("Preparing ansible.cfg file and archiving old logs")
    #move old logs to archive
    cmdArchive = "mv /data/log/NokiaNSW/*CZ* /data/log/NokiaNSW/Archive"    
    os.system(cmdArchive)                                               
    
    global LO
    log_path = f"log_path=/data/log/NokiaNSW/Ansible/ansible_{LO}.log"
    
    #create new config file
    cmdConfig = "cp /etc/ansible/ansible.ori /etc/ansible/ansible.cfg"
    os.system(cmdConfig)
    
    print(f"Log path='{log_path}' to /etc/ansible/ansible.cfg") 
    with open("/etc/ansible/ansible.cfg", "a") as cfg:
        cfg.writelines(f"{log_path}\n") 

if __name__ == '__main__':
    
    servers = getServers()
    print("----------------------------------------------------------------\n")
    getPasswd(servers)
    print("----------------------------------------------------------------\n")
    print(f"Leagy Order:{LO}")
    print("Servers data:")
    for key, value in servers.items():
        print(f"{key}: {value}")
    print("----------------------------------------------------------------\n")
    writeIpmapping(servers)
    print("----------------------------------------------------------------\n")
    writeHosts(servers)
    print("----------------------------------------------------------------\n")
    ansibleLogs()
    #powerState()
    print("Preparation for ansible is done")
