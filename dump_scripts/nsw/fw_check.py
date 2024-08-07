#!/usr/bin/python3

# Using data from /data/sfng/ipmapping

import subprocess
import os
import re
import time
import json

from datacollection_gen11 import (
    get_servers,
    handle_multiproc,
    get_lo,
    ping_server,
    print_servers,
)

FAIL_PREFIX = "\033[91m"
OK_PREFIX = "\033[92m"
INFO_PREFIX = "\033[96m"
MIRECEK_PANTOFLE = "\033[95m"
POSTFIX = "\033[0m"

JSON_LOGS = "/data/log/NokiaNSW/"
ANSIBLE_LOGS = "/data/log/NokiaNSW/Ansible/"
IPMAPPING = "/data/sfng/ipmapping"
HOSTS = "/etc/ansible/hosts"
DATACOLLECTION_LOG = "/data/sfng/log/"
POLARIS_REQUEST = "https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER="
FW_FULL = "FW_full.txt"
FW_REDUCED = "FW_reduced.txt"


GEN10 = {
    "HPE Eth 10/25Gb 2P 641SFP28 Adptr": "16.28.1002",
    "iLO 5": "2.72 Sep 04 2022",
    "Redundant System ROM": "v2.68 (07/14/2022)",
    "System ROM": "v2.68 (07/14/2022)",
}


GEN10PLUS = {
    "Mellanox ConnectX-6 LX OCP3.0": "26.33.1048",
    "iLO 5": "2.72 Sep 04 2022",
    "Redundant System ROM": "U46 v1.64 (08/11/2022)",
    "System ROM": "U46 v1.64 (08/11/2022)",
    "Nvidia Network Adapter": "26.33.1048",
    "HPE MR216i-a Gen10+": "52.16.3-4455",
}

GEN11 = {
    "iLO 6": "1.53 Oct 10 2023",
    "Redundant System ROM": "U54 v1.46 (09/26/2023)",
    "System ROM": "U54 v1.46 (09/26/2023)",
    "HPE MR216i-o Gen11": "52.24.3-4948",
    "Mellanox ConnectX-6 LX OCP3.0": "26.37.1700",
    "Mellanox Network Adapter": "26.37.1700",
    "Server Platform Services (SPS) Firmware": "6.0.4.75.0",
    "HPE SN1610E 32Gb 2p FC HBA": "14.2.589.5",
}

GEN11_2023_10 = {
    "iLO 6": "1.56 Jan 27 2024",
    "Redundant System ROM": "U54 v2.12 (12/13/2023)",
    "System ROM": "U54 v2.12 (12/13/2023)",
    "HPE MR216i-o Gen11": "52.24.3-4948",
    "Mellanox ConnectX-6 LX OCP3.0": "26.37.1700",
    "Mellanox Network Adapter": "26.37.1700",
    "Server Platform Services (SPS) Firmware": "6.1.4.05.0",
    "HPE SN1610E 32Gb 2p FC HBA": "14.2.589.5",
    "Intelligent Platform Abstraction Data": "10.0.0 Build 47",
}

GEN10PLUS_2023_10_09_03 = {
    "Ethernet 10/25Gb 2-port SFP28 MCX512F-ACHT Adapter": "16.35.3006",
    "Ethernet 10/25Gb 2-port SFP28 MCX562A-ACAI OCP3 Adapter": "16.35.3006",
    "iLO 5": "3.00 Dec 14 2023",
    "Redundant System ROM": "U46 v1.90 (10/19/2023)",
    "System ROM": "U46 v1.90 (10/19/2023)",
    "HPE MR216i-a Gen10+": "52.24.3-4948",
    "Mellanox ConnectX-6 LX OCP3.0": "26.37.1700",
    "Mellanox Network Adapter": "26.37.1700",
}

GEN11_2023_10_00_00 = {
    "iLO 6": "1.53 Oct 10 2023",
    "Redundant System ROM": "U54 v1.46 (09/26/2023)",
    "System ROM": "U54 v1.46 (09/26/2023)",
    "HPE MR216i-o Gen11": "52.24.3-4948",
    "Mellanox ConnectX-6 LX OCP3.0": "26.37.1700",
    "Mellanox Network Adapter": "26.37.1700",
}

GEN11_2024_04_00_00 = {
    "iLO 6": "1.58 Mar 22 2024",
    "Redundant System ROM": "A56 v1.58 (01/04/2024)",
    "System ROM": "A56 v1.58 (01/04/2024)",
    "HPE MR216i-o Gen11": "52.26.3-5379",
    "Mellanox ConnectX-6 LX OCP3.0": "26.40.1000",
    "Mellanox Network Adapter": "26.40.1000",
}


PARAMS = [
    ("Gen10", GEN10),
    ("Gen10P+", GEN10PLUS),
    ("2023.09.00.03 Gen10+", GEN10PLUS_2023_10_09_03),
    ("GEN11", GEN11),
    ("GEN11_2023_10", GEN11_2023_10),
    ("2023.10.00.00 Gen11", GEN11_2023_10_00_00),
    ("2024.04.00.00 Gen11", GEN11_2024_04_00_00),
]


def get_ilorest(server_name, server_info):
    """get info about server using ilorest"""
    ip, user, password = server_info["IP"], server_info["USER"], server_info["PSWD"]
    command = f"ilorest serverinfo --firmware --url {ip} -u {user} -p {password}"

    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, check=False
    )
    server_info["FW"] = result.stdout

    return server_name, result.returncode, result.stdout, result.stderr


def write_server_fw(servers, lo):
    f"""Write servers fw to {DATACOLLECTION_LOG}{lo}/{FW_FULL}"""

    fw_full = f"{DATACOLLECTION_LOG}{lo}/{FW_FULL}"
    with open(fw_full, "w") as fw_full:
        for sn, data in servers.items():
            fw_full.write(f'{sn}: {data["IP"]}  {data["UL"]}\n')
            fw_full.write(f'{data["FW"]}')
            fw_full.write(f"\n{'-'*40}\n")


def check_fw(servers, params, lo):
    """comparing actual server fw to expected"""
    summary = {}
    failed_servers = {}

    for sn, info in servers.items():
        print("="*40)
        datacollection = info["FW"].split("\n")
        for fw, vr in params.items():
            flag = 0
            for data in datacollection:
                if fw in data:
                    if vr not in data:
                        flag = 1
                        print("\033[91m" + f"FAIL: {data} != {vr}" "\033[0m")
                        if vr not in failed_servers.keys():
                            failed_servers[vr] = []
                        if [sn, info["IP"], info["PSWD"]] not in failed_servers[vr]:
                            failed_servers[vr].append([sn, info["IP"], info["PSWD"]])
                    else:
                        print("\033[92m" + f"OK: {data} == {vr}" + "\033[0m")
                    if "Mellanox Network Adapter" in data:
                        name = data.split("-")[0]
                        version = data.split(":")[-1]
                        data = name + version
                    if data in summary.keys():
                        summary[data] += 1
                    else:
                        summary[data] = 1
            if flag == 0:
                print("\033[92m" + "Everything is OK" + "\033[0m")

    with open(f"{DATACOLLECTION_LOG}{lo}/{FW_REDUCED}", "w") as f:
        for k, v in summary.items():
            f.write(f"{k}   {v}\n")

    count_disks()

    for key, srvrs in failed_servers.items():
        print(f"{FAIL_PREFIX}FAILED fw: {key}{POSTFIX}")
        for server in srvrs:
            print(INFO_PREFIX, server[0], server[1], server[2], POSTFIX, "\n")


def get_model(lo):
    f"""get server model for {lo}"""
    generation = None
    pattern = r"\b\d{4}\.\d{2}\.\d{2}\.\d{2} (?:Gen10\+?|Gen11)\b"

    with open(f"{ANSIBLE_LOGS}/ansible_{lo}.log", "r") as log:
        header = log.readline().strip()
        if model := re.search(pattern, header):
            print(model.group(0))
            for i in PARAMS:
                if model.group(0) in i:
                    print(f"{INFO_PREFIX}Used spp: {i[0]}{POSTFIX}")
                    return i[1]

    while not generation:
        print("Can't find model in ansible logs.")
        print("Please select model manualy.")
        for index, param in enumerate(PARAMS, 1):
            print(f"{index}. {param[0]}")

        model_index = int(input(">>"))
        if len(PARAMS) <= model_index < 0:
            print("Index out of bound")
        else:
            generation = PARAMS[model_index - 1][1]

    print(f"{INFO_PREFIX}Going to use {PARAMS[model_index - 1][0]}{POSTFIX}")
    return generation


def count_disks():
    nvme = "NVMe/SAS"
    sata = "960GB 6G SATA SSD"
    nvme_count = 0
    sata_count = 0

    print(f"{INFO_PREFIX}\n{'-'*40}\nCounting disks: {POSTFIX}")

    with open(f"{DATACOLLECTION_LOG}{lo}/{FW_FULL}", "r") as file:
        content = file.read()
        nvme_count = content.count(nvme)
        sata_count = content.count(sata)
        print(f"{MIRECEK_PANTOFLE}{nvme}: {nvme_count}{POSTFIX}")
        print(f"{MIRECEK_PANTOFLE}{sata}: {sata_count}{POSTFIX}")

    with open(f"{DATACOLLECTION_LOG}{lo}/{FW_REDUCED}", "a") as f:
        f.write(f"{nvme}:   {nvme_count}\n")
        f.write(f"{sata}:   {sata_count}")


if __name__ == "__main__":
    servers = get_servers()

    print(INFO_PREFIX + "Pinging servers." + POSTFIX)
    handle_multiproc(servers, ping_server)
    lo = get_lo(servers)
    fw_template = get_model(lo)

    lo_logs = f"{DATACOLLECTION_LOG}{lo}"
    if os.path.exists(lo_logs):
        print(f"{OK_PREFIX}Folder {lo_logs} already exist.{POSTFIX}")
    else:
        print(f"{MIRECEK_PANTOFLE}Creating /data/sfng/log/{lo} directory{POSTFIX}")
        os.mkdir(lo_logs)

    print("\nGetting server info using ilorest.")
    handle_multiproc(servers, get_ilorest)
    print(f"\nWriting result to {DATACOLLECTION_LOG}{lo}/FW_check_full.txt")
    write_server_fw(servers, lo)
    print(f"\nComparing acrual fw with fw from template.")
    check_fw(servers, fw_template, lo)
