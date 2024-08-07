#!/usr/bin/python3

import os
import subprocess
import sys
import time

def get_servers_mr216():
    template = 'grep -ril MR216 /data/log/NokiaNSW/*.json | cut -d "/" -f 5 | cut -d "." -f 1 | cut -d "_" -f 3'
    result = subprocess.run([template], shell=True, stdout = subprocess.PIPE)
    
    sns = result.stdout.decode('utf-8').split("\n")
    # length of standart SN i.e. CZ233102GY
    sns = [i for i in sns if len(i) == 10]
    servers = {}
    for sn in sns:
        ip_template = f'grep {sn} /etc/ansible/hosts | cut -f 2 | cut -d "=" -f 2'
        ip_tmp = subprocess.run([ip_template], shell=True, stdout = subprocess.PIPE)

        psw_template = f'grep {sn} /etc/ansible/hosts | cut -f 3 | cut -d "=" -f 2'
        psw_tmp = subprocess.run([psw_template], shell=True, stdout = subprocess.PIPE)

        servers[sn] = {}
        servers[sn]["IP"] = ip_tmp.stdout.decode("utf-8").strip()         
        servers[sn]["PSWD"] = psw_tmp.stdout.decode("utf-8").strip()
    
    return servers

#def get_servers_data(filename):
#    servers = {}
#    with open(filename) as file:
#        for line in file:
#            sn, ip, pswd = [i for i in line.split("\t") if len(i) != 0]
#            sn = sn[3:]
#            servers[sn] = {}
#            servers[sn]["IP"] = ip.split("=")[1]
#            servers[sn]["PSWD"] = pswd.split("=")[1].strip()
#
#    return servers

def generate_cfg(servers):
    template = ""

    with open("reset.xml", "r") as file:
        template = file.read()


    for server in servers.keys():
        filedata = template
        filedata = filedata.replace("{PSWD}", servers[server]["PSWD"])
    
        filename = f"reset_{server}.xml"
        print(f"Writing config to {filename}:") 
        print(filedata)
        print()

        with open(filename, "w") as cfg:
            cfg.write(filedata) 

def print_servers(servers):
    for server in servers.keys():
        print(f"{server}: {servers[server]}")

def run_config(servers):
    logfile =  time.strftime(f"%l_%M_%b%d_%Y")
    logfile += ".txt"
    os.system(f"touch {logfile}")    

    for server in servers.keys():
        if "IP" in servers[server]:
            command = f"perl locfg.pl -f reset_{server}.xml  -ilo5 -s {servers[server]['IP']} -u Administrator  -p {servers[server]['PSWD']} >> {logfile}"
            print(command)
            os.system(f'echo {command} >> {logfile}')
            os.system(f"perl locfg.pl -f reset_{server}.xml  -ilo5 -s {servers[server]['IP']} -u Administrator  -p {servers[server]['PSWD']} >> {logfile}")
            time.sleep(3)
        else:
            print(f"Can't find url for {server}")
    

if __name__ == "__main__":
    
    print("Looking for servers with MR216 controller:")
    servers = get_servers_mr216()
    print_servers(servers)
    
    print("\n------------------------------------\n")
    print("Generating servers config:")
    generate_cfg(servers)
    
    action = input("Start reset(y/n)?:")
    if action == 'y':
        print("Runing reset:")
        run_config(servers)
    else:
        print("Skipping reset")
    
    print("\n---------------------------------------------\n")
    clear = input("remove cfg files(y/n)?: ")
    if clear == 'y':
        os.system("rm *CZ*.xml")

    print("\n---------------------------------------------\n")
    print("Wait few minutes and check result of iloconfig with: my_info {IP}")
    for sn in servers.keys():
        print(f'{sn}: {servers[sn]["IP"]}')
