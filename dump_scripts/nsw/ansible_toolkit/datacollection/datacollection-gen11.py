#!/usr/bin/env python3

import os
import json
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

JSON_LOGS = "/data/log/NokiaNSW"
IPMAPPING = "/data/sfng/ipmapping"
HOSTS = "/etc/ansible/hosts"
DATACOLLECTION_LOG = "/data/sfng/log"
POLARIS_REQUEST = "https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER="


def get_servers():
    servers = {}

    with open(IPMAPPING, "r") as ipmap:
        for line in ipmap:
            extracted = line.split("\t")
            extracted = [s for s in extracted if s != ""]
            sn, ip, ul = extracted
            ul = ul.rstrip()
            servers[sn] = {}
            servers[sn]["IP"] = ip
            servers[sn]["UL"] = ul
            servers[sn]["USER"] = "Administrator"

    with open(HOSTS, "r") as hosts:
        for line in hosts:
            if "ILOCZ" in line:
                extracted = line.split("\t")
                extracted = [i for i in extracted if i != ""]
                sn, ip, pswd = extracted
                servers[sn[3:]]["PSWD"] = pswd.split("=")[1].strip()

    return servers


def print_servers(servers):

    for sn, data in servers.items():
        print(f"{sn} --> {data}")


def handle_multiproc(servers, func):
    results = []

    with ThreadPoolExecutor(max_workers=len(servers)) as executor:
        future_to_server = {
            executor.submit(func, server_name, server_info): server_name
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
            print(f"Failed  to {func.__doc__}, check ilo for:")
            print(
                f'{server_name}:\t{servers[server_name]["IP"]}\t{servers[server_name]["USER"]}\t{servers[server_name]["PSWD"]}'
            )
        else:
            print(f"Success for {server_name}")
            

    return results


def ping_server(server_name, server_info):
    """Ping server"""
    print(server_name, server_info)
    command = f'ping -w 2 {server_info["IP"]}'
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, check=False
    )
    return server_name, result.returncode, result.stdout, result.stderr


def get_lo(servers):

    for sn, _ in servers.items():
        request = requests.get(f"{POLARIS_REQUEST}{sn}")
        if request.status_code == 200:
            tmp = json.loads(request.text)
            return tmp["DATA"]["LEGACY_ORDER"]
    return None


def get_polaris_info(server_name, server_info={}):
    "get info from polaris"
    request = requests.get(f"{POLARIS_REQUEST}{server_name}")
    response = json.loads(request.text)
    server_info["DATA"] = response["DATA"]
    return_code = 0 if request.status_code == 200 else 1
    return server_name, return_code, server_info, request.status_code


def get_redfish(endpoint, server_info):
    ip, user, password = server_info["IP"], server_info["USER"], server_info["PSWD"]
    url =  f'https://{ip}{endpoint}'
    request = requests.get(url, auth=HTTPBasicAuth(user, password), verify=False)
    response = json.loads(request.text)

    return response, request.status_code


def get_enclosure(server_name, server_info):
    "get enclosure info"
    endpoint = "/redfish/v1/Chassis/1/"
    response, status_code = get_redfish(endpoint, server_info)

    server_info["ENCLOSURE"] = {"Model": response["Model"], "SKU": response["SKU"]}

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code

def get_ilo(server_name, server_info):
    "get ilo info"
    endpoint = "/redfish/v1/Managers/1/"
    response, status_code = get_redfish(endpoint, server_info)

    server_info["ILO_INFO"] = {"MAC": server_info["DATA"]["ILO_MAC"], 
        "FW": response["Oem"]["Hpe"]["Firmware"]["Current"]["VersionString"]}

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_bios_cpu(server_name, server_info):
    "get bios/cpu info"
    endpoint = "/redfish/v1/systems/1/"
    response, status_code = get_redfish(endpoint, server_info)                                                                                               # parse IPMAPPING and get server info
    server_info["CPU_BIOS"] = {
        "BIOS FW": response["BiosVersion"],
        "UUID": response["UUID"],
        "CPU Count": response["ProcessorSummary"]["Count"],
        "CPU Type": response["ProcessorSummary"]["Model"],
        "RAM Memory Size": f'{response["MemorySummary"]["TotalSystemMemoryGiB"]}GB'
    }
                                                                                
    return_code = 0 if status_code == 200 else 1                                
    return server_name, return_code, server_info, status_code                   


def get_dimms(server_name, server_info):
    "get dimms info"
    server_info["DIMMS"] = []
    enabled_dimms = 0
    for p in range(1, 3):
        for d in range(1, 16):
            endpoint = f"/redfish/v1/systems/1/Memory/proc{p}dimm{d}"
            response, status_code = get_redfish(endpoint, server_info)
            if response["Status"]["State"] == "Enabled":
                enabled_dimms += 1
                slot = f'P{p}D{d} DIMM Check'
                data = f'PROC: {p} DIMM: {d} SIZE: {response["CapacityMiB"]} PN: {response["PartNumber"]} '
                server_info["DIMMS"].append({slot: data})

    return_code = 0 if status_code == 200 else 1                                   
    return server_name, return_code, server_info, status_code                   


def get_disks(server_name, server_info):
    "get disks info"
    controllers_endpoints = f'/redfish/v1/systems/1/Storage'
    storage, status_code = get_redfish(endpoint, server_info)
    controllers = storage["Members"]

    for index, controller in enumerate(controllers):
        controller_endpoint = controller["@odata.id"]
        




if __name__ == "__main__":
    # ping all servers
    servers = get_servers()

    print("Pinging servers.")
    handle_multiproc(servers, ping_server)
    
    cont = input("Do you want to proceed? [y/n]: ")
    if cont in ["n", "N", "no", "NO"]:
        print("Canceling execution.")
        exit(1)

    print("Getting LO number.")
    LO = get_lo(servers)
    if not LO:
        print("Failed to get LO. Canceling execution.")
        exit(1)

    lo_logs = f"{DATACOLLECTION_LOG}/{LO}"
    if os.path.exists(lo_logs):
        print(f"Folder {lo_logs} already exist.")
    else:
        print(f"Creating /data/sfng/log/{LO} directory")
        os.mkdir(lo_logs)

    print("Getting server info from polaris.")
    handle_multiproc(servers, get_polaris_info)

    print("getting enclosure info.")
    handle_multiproc(servers, get_enclosure)

    print("getting ilo info.")
    handle_multiproc(servers, get_ilo)

    print("getting bios/cpu info.")
    handle_multiproc(servers, get_bios_cpu)

    print("getting memory info.")
    handle_multiproc(servers, get_dimms)


    print_servers(servers)