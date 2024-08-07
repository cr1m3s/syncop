#!/usr/bin/python3

import os
import subprocess
import sys
import time

def get_servers_data(filename):
    servers = {}
    with open(filename) as file:
        for line in file:
            sn, pswd, device, host, ip, mask, gateway  = line.split("\t")
            servers[sn] = {}
            servers[sn]["IP"] = ip
            servers[sn]["PSWD"] = pswd
            servers[sn]["MASK"] = mask
            servers[sn]["HOST"] = host
            servers[sn]["GATEWAY"] = gateway.strip()

    return servers

def generate_cfg(servers):
    template = ""

    with open("ilo_cfg_full.xml", "r") as file:
        template = file.read()


    for server in servers.keys():
        filedata = template
        filedata = filedata.replace("{PSWD}", servers[server]["PSWD"])
        filedata = filedata.replace("{MASK}", servers[server]["MASK"])
        filedata = filedata.replace("{IP}", servers[server]["IP"])      
        filedata = filedata.replace("{GATEWAY}", servers[server]["GATEWAY"])
        filedata = filedata.replace("{HOST}", servers[server]["HOST"])      
    
        filename = f"ilo_cfg_{server}.xml"
        print(f"Writing config to {filename}:") 
        print(filedata)
        print()

        with open(filename, "w") as cfg:
            cfg.write(filedata) 

def get_servers_url(servers):
    subprocess.run(["systemctl", "restart", "dhcpd.service"])
    
    result = subprocess.run(["dhcp-lease-list | grep ILO | awk '{print $2,$3}'"], stdout=subprocess.PIPE, shell=True)
    out1 = result.stdout.decode('utf-8')
    
    output = out1.split("\n")
    
    for i in output:
        res = i.split(" ")
        if(len(res) == 2):
            ip = res[0]
            sn = res[1]
            if sn[3:] not in servers.keys():
                print(f"{sn[3:]} not in dhcp list")
            else:
                servers[sn[3:]]["URL"]=ip
    
    return servers

def print_servers(servers):
    for server in servers.keys():
        print(f"{server}: {servers[server]}")

def run_config(servers):
    logfile =  time.strftime(f"%l_%M_%b%d_%Y")
    logfile += ".txt"
    os.system(f"touch {logfile}")    

    for server in servers.keys():
        if "URL" in servers[server]:
            command = f"perl locfg.pl -f ilo_cfg_{server}.xml  -ilo5 -s {servers[server]['URL']} -u Administrator  -p {servers[server]['PSWD']} >> {logfile}"
            print(command)
            os.system(f'echo {command} >> {logfile}')
            os.system(f"perl locfg.pl -f ilo_cfg_{server}.xml  -ilo5 -s {servers[server]['URL']} -u Administrator  -p {servers[server]['PSWD']} >> {logfile}")
            time.sleep(3)
        else:
            print(f"Can't find url for {server}")
    

if __name__ == "__main__":
    
    if len(sys.argv) != 2:
        print("usage: ./reader.py filename.txt")
        exit(1)
    filename = sys.argv[1]
    
    print("Reading txt data")
    servers = get_servers_data(filename)
    
    print("\n------------------------------------\n")
    print("Getting servers url:")
    servers = get_servers_url(servers)
    print_servers(servers)
    
    print("\n------------------------------------\n")
    print("Generating servers config:")
    generate_cfg(servers)
    print_servers(servers)
    
    action = input("Start configuration(y/n)?:")
    if action == 'y':
        print("Runing configuration:")
        run_config(servers)
    else:
        print("Skipping configuration")
    
    print("\n---------------------------------------------\n")
    clear = input("remove cfg files(y/n)?: ")
    if clear == 'y':
        os.system("rm *CZ*.xml")

