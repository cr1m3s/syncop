#!/usr/bin/env python3

import subprocess

def get_server_info():
    hosts = subprocess.run(["cat /etc/ansible/hosts | grep CZ"], stdout=subprocess.PIPE, shell=True)
    hosts_info = hosts.stdout.decode('utf-8').split("\n")

    ulocs = subprocess.run(["cat /data/sfng/ipmapping | grep CZ"], stdout=subprocess.PIPE, shell=True)
    ulocs_info = ulocs.stdout.decode('utf-8').split("\n")

    servers = {}

    for line in hosts_info:
        extracted = line.split("\t")
        extracted = [s for s in extracted if s != '']
        if len(line) > 30:
            sn, ip, psw = extracted 
            sn = sn[3:]
            servers[sn] = {}
            servers[sn]["IP"] = ip
            servers[sn]["PSWD"] = psw
    
    for line in ulocs_info:
        if len(line) < 20:
            break
        extracted = line.split("\t")
        extracted = [s for s in extracted if s != '']
        sn, ip, uloc = extracted
        servers[sn]["ULOC"] = uloc

    return servers

def get_files(keyword):
    command = f"ls /data/log/NokiaNSW | grep {keyword}"
    ls_spp = subprocess.run([command], stdout=subprocess.PIPE, shell=True)
    return ls_spp.stdout.decode('utf-8')

def check_passed(servers, logs):
    fail_count = 0

    for sn, info in servers.items():
        if sn not in logs:
            print("\n" + f"{sn}" + '\033[93m' + "  NOT PASSED" + '\033[0m')
            print(f'SN: {sn} {info["IP"]}  {info["PSWD"]} {info["ULOC"]}')
            fail_count += 1
        else:
            print(f"{sn}" + '\033[92m' + "  PASSED" + '\033[0m')
    return fail_count


if __name__ == '__main__':
    servers = get_server_info()
    servers_count = len(servers.keys())

    first_spp = get_files("ilorest")
    second_spp = get_files("bios")

    if failed := check_passed(servers, first_spp):
        print("First spp check failed.")
        print('\033[94m' + f"Passed: {servers_count - failed} servers from {servers_count}" + '\033[0m')
        exit(0)
    print(f"\nFirst spp done! All {servers_count} servers passed.")

    if failed := check_passed(servers, second_spp):
        print("Second spp check failed.")
        print('\033[94m' + f"Passed: {servers_count - failed} servers from {servers_count}" + '\033[0m')
        exit(0)
    print(f"\nSecond spp done! All {servers_count} servers passed.")
