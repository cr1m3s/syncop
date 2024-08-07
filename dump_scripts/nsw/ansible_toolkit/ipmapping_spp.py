#!/usr/bin/env python3

import os
import subprocess
import json
import asyncio
import aiohttp
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

LO = ''
MODEL = ''
SERVERS = {}

def getServers():

    uloc_servers = {}
    with open("uloc.txt", "r", encoding='utf-8') as file:
        for line in file:
            s_data = line.split("\t")
            sn = s_data[0]
            uloc = s_data[1].rstrip()
            uloc_servers[sn] = uloc

    subprocess.run(["systemctl", "restart", "dhcpd.service"], check=False)

    result = subprocess.run(["dhcp-lease-list | grep ILO | awk '{print $2,$3}'"], stdout=subprocess.PIPE, shell=True, check=False)
    out1 = result.stdout.decode('utf-8')
    output = out1.split("\n")
    ip_servers = {}

    for i in output:
        res = i.split(" ")
        if len(res) == 2:
            ip = res[0]
            sn = res[1][3:]
            ip_servers[sn] = ip

    global SERVERS
    for key, _ in uloc_servers.items():
        if key not in ip_servers:
            print(f"Can't find {key} in dhcp-lease-list\n")
            sys.exit(1)
        else:
            SERVERS[key] = {}
            SERVERS[key]["UL"] = uloc_servers[key]
            SERVERS[key]["IP"] = ip_servers[key]

    for key, value in SERVERS.items():
        print(f"{key}->{value}")    


async def fetch(session, sn):
    url = f"https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER={sn}"
    async with session.get(url) as response:
        if response.status != 200:
            print(f"Failed request {response.status}.")
            sys.exit(1)
        print(f"Retriewing data for {sn}") 
        tmp = json.loads(await response.text())
        lo = tmp["DATA"]["LEGACY_ORDER"]
        global LO
        if LO == '':
            LO = lo
        if lo != LO:
            print(f"SN: {sn} have different LO:{lo} than previous servers: {LO}")
            sys.exit(1)
        pswd = tmp["DATA"]["ILO_PASSWORD"]
        if len(pswd) != 8:
            print("Something wrong with password!")                
            print(f"Check pswd: {pswd} for SN:{sn}")

        global SERVERS 
        SERVERS[sn]["PSWD"] = pswd 

        print(f"{sn} --> {pswd}")


async def fetch_all(sns):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, sn) for sn in sns]
        await asyncio.gather(*tasks)


def writeIpmapping(servers):
    IPMAPPING = "/data/sfng/ipmapping"
    print(f"Writing servers data to {IPMAPPING}")
    with open(IPMAPPING, "w") as file:
        for key in servers.keys():
            print(f'{key}\t{servers[key]["IP"]}\t{servers[key]["UL"]}\n')
            file.write(f'{key}\t{servers[key]["IP"]}\t{servers[key]["UL"]}\n')


def write_hosts(servers):
    ANSIBLE_HOSTS = "/etc/ansible/hosts"
    print(f"Writing servers data to {ANSIBLE_HOSTS}")
    prepCmd = f"cp /etc/ansible/nokia.ori {ANSIBLE_HOSTS}"
    os.system(prepCmd)

    with open(ANSIBLE_HOSTS, "a", encoding='utf-8') as file:
        for key in servers:
            print(f'ILO{key}\tbaseuri={servers[key]["IP"]}\tpassword={servers[key]["PSWD"]}\n')
            file.write(f'ILO{key}\tbaseuri={servers[key]["IP"]}\tpassword={servers[key]["PSWD"]}\n')


def check_power_state(server_name, server_info, username):
    command = (
        f'ilorest get PowerState --selector=ComputerSystem. '
        f'--url {server_info["IP"]} -u {username} -p {server_info["PSWD"]} | grep PowerState'
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
    return server_name, result.returncode, result.stdout, result.stderr


def power_state(servers):
    username = "Administrator"
    results = []

    with ThreadPoolExecutor(max_workers=len(servers)) as executor:
        future_to_server = {
            executor.submit(check_power_state, server_name, server_info, username): server_name
            for server_name, server_info in servers.items()
        }

        for future in as_completed(future_to_server):
            server_name = future_to_server[future]
            try:
                server_name, returncode, stdout, stderr = future.result()
                results.append((server_name, returncode, stdout, stderr))
            except Exception as exc:
                results.append((server_name, None, None, str(exc)))

    for result in results:
        server_name, returncode, stdout, stderr = result
        if returncode != 0:
            print("Failed ilorest request, check ilo for:")
            print(f'{server_name}:\t{servers[server_name]["IP"]}\t{username}\t{servers[server_name]["PSWD"]}')
        else:
            print(f'Success for {server_name}: {stdout.strip()}')


def ansible_logs():
    """Move old logs to archive"""
    print("Preparing ansible.cfg file and archiving old logs")
    #move old logs to archive
    cmd_archive = "mv /data/log/NokiaNSW/*CZ* /data/log/NokiaNSW/Archive"
    os.system(cmd_archive)

    global LO
    log_path = f"log_path=/data/log/NokiaNSW/Ansible/ansible_{LO}.log"

    #create new config file
    cmd_config = "cp /etc/ansible/ansible.ori /etc/ansible/ansible.cfg"
    os.system(cmd_config)

    print(f"Log path='{log_path}' to /etc/ansible/ansible.cfg")
    with open("/etc/ansible/ansible.cfg", "a", encoding='utf-8') as cfg:
        cfg.writelines(f"{log_path}\n")
    
    with open(log_path, "w") as log:
        global MODEL
        log.write(' '.join((str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "    ---------> Model selected |", str(MODEL), "\n")))


def main_menu():
    print("\nNokia NFVi - select generation:")
    print("[1] for NFVi3 Gen10+")
    print("[2] for NFVi4 Gen11")
    choice = input (": ")
    if choice == "1":
        gen10_menu()
    elif choice == "2":
        gen11_menu()
    else:
        main_menu()


def gen10_menu():
    print("\nNokia NFVi3 Gen10+ - select MODEL:")
    print("[1] for P73546-B21    NCS 22.7 PP1    SPP 2023.03.00.00")
    print("[2] for P73545-B21    CBIS 22 FP1     SPP 2023.03.00.00")
    print("[3] for P73549-B21    CBIS 24         SPP 2023.09.00.03")
    print("[4] for P73548-B21    NCS 23.10       SPP 2023.09.00.02")
    print("[5] for P73547-B21    NCS 22.12 MP1   SPP 2023.09.00.04")
    print("[0] back to main menu")
    global MODEL
    choice = input (": ")
    if choice == "1":
        MODEL = "P73546-B21    NCS 22.7 PP1    SPP 2023.03.00.00 Gen10+"
    elif choice == "2":
        MODEL = "P73545-B21    CBIS 22 FP1     SPP 2023.03.00.00 Gen10+"
    elif choice == "3":
        MODEL = "P73549-B21    CBIS 24         SPP 2023.09.00.03 Gen10+"
        os.system("cp /var/www/html/boot/script_menu_gen10_SPP2023.09.03.pl /var/www/html/boot/script_menu.pl")
    elif choice == "4":
        MODEL = "P73548-B21    NCS 23.10       SPP 2023.09.00.02 Gen10+"
    elif choice == "5":
        MODEL = "P73547-B21    NCS 22.12 MP1   SPP 2023.09.00.04 Gen10+"
    elif choice == "0":
        main_menu()
    else:
        gen10_menu()


def gen11_menu():
    print("\nNokia NFVi4 Gen11 - select MODEL :")
    print("[1] for P73548-B21    NCS 23.10       SPP 2023.10.00.00")
    print("[2] for P73549-B21    CBIS 24         SPP 2024.04.00.00")
    print("[3] for P73550-B21    NCP 23.11       SPP 2023.10.00.02")
    print("[0] back to main menu")
    global MODEL
    choice = input (": ")
    if choice == "1":
        MODEL = "P73548-B21    NCS 23.10       SPP 2023.10.00.00 Gen11"
        os.system("cp /var/www/html/boot/script_menu_gen11_SPP2023.10.00.pl /var/www/html/boot/script_menu.pl")
    elif choice == "2":
        MODEL = "P73549-B21    CBIS 24         SPP 2024.04.00.00 Gen11"
        os.system("cp /var/www/html/boot/script_menu_gen11_SPP2024.04.00.pl /var/www/html/boot/script_menu.pl")
    elif choice == "3":
        MODEL = "P73550-B21    NCP 23.11       SPP 2023.10.00.02 Gen11"
        os.system("cp /var/www/html/boot/script_menu_gen11_SPP2023.10.02.pl /var/www/html/boot/script_menu.pl")
    elif choice == "0":
        main_menu()
    else:
        gen11_menu()


if __name__ == '__main__':
    getServers()
    print("----------------------------------------------------------------\n")
    asyncio.run(fetch_all(SERVERS))
    print("----------------------------------------------------------------\n")
    print(f"Leagy Order:{LO}")
    print("Servers data:")
    for key, value in SERVERS.items():
        print(f"{key}: {value}")
    print("----------------------------------------------------------------\n")
    writeIpmapping(SERVERS)
    print("----------------------------------------------------------------\n")
    write_hosts(SERVERS)
    print("ilo communication check")
    power_state(SERVERS)
    print("----------------------------------------------------------------\n")
    main_menu()
    print("----------------------------------------------------------------\n")
    ansible_logs()
    print("----------------------------------------------------------------\n")    
    print("Preparation for ansible is done")
