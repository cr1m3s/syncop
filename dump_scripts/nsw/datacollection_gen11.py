#!/usr/bin/env python3

import os
import json
import itertools
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

JSON_LOGS = "/data/log/NokiaNSW/"
IPMAPPING = "/data/sfng/ipmapping"
HOSTS = "/etc/ansible/hosts"
DATACOLLECTION_LOG = "/data/sfng/log/"
POLARIS_REQUEST = "https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER="

FAIL_PREFIX = "\033[91m"
OK_PREFIX = "\033[92m"
INFO_PREFIX = "\033[96m"
MIRECEK_PANTOFLE = "\033[95m"
POSTFIX = "\033[0m"


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

    workers = len(servers)

    #    for i in ["dimm", "disk"]:
    #        if i in func.__doc__:
    #            workers = 8

    with ThreadPoolExecutor(max_workers=workers) as executor:
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
            print(FAIL_PREFIX + f"Failed  to {func.__doc__}, check ilo for:" + POSTFIX)
            print(
                f'{server_name}:\t{servers[server_name]["IP"]}\t{servers[server_name]["USER"]}\t{servers[server_name]["PSWD"]}'
            )
        else:
            print(
                OK_PREFIX
                + f"Success to {func.__doc__} for server {server_name}"
                + POSTFIX
            )

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
    url = f"https://{ip}{endpoint}"
    request = requests.get(url, auth=HTTPBasicAuth(user, password), verify=False)
    response = json.loads(request.text)

    return response, request.status_code


def get_enclosure(server_name, server_info):
    "get enclosure info"
    endpoint = "/redfish/v1/Chassis/1/"
    response, status_code = get_redfish(endpoint, server_info)

    server_info["ENCLOSURE"] = [
        f'Enclosure Type:, {response["Model"]}',
        f'PN from OEM, {response["SKU"]}',
        f'SN from OEM, {response["SerialNumber"]}' f'SKU:, {response["SKU"]}',
    ]

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_ilo(server_name, server_info):
    "get ilo info"
    endpoint = "/redfish/v1/Managers/1/"
    response, status_code = get_redfish(endpoint, server_info)

    server_info["ILO_INFO"] = [
        f'iLO MAC Address, {server_info["DATA"]["ILO_MAC"]}',
        f'iLO FW Version, {response["Oem"]["Hpe"]["Firmware"]["Current"]["VersionString"]}',
        f'iLO Advanced License Key, {server_info["DATA"]["LICENSES"][0]["KEY"]}',
        f'iLO OEM Password, {server_info["DATA"]["ILO_PASSWORD"]}',
    ]

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_bios_cpu(server_name, server_info):
    "get bios/cpu info"
    endpoint = "/redfish/v1/systems/1/"
    response, status_code = get_redfish(endpoint, server_info)
    server_info["CPU_BIOS"] = [
        f'BIOS FW:, {response["BiosVersion"]}',
        f'UUID:, {response["UUID"]}',
        f'CPU Count:, {response["ProcessorSummary"]["Count"]}',
        f'CPU Type:, {response["ProcessorSummary"]["Model"]}',
        f'RAM Memory Size:, {response["MemorySummary"]["TotalSystemMemoryGiB"]}GB',
    ]

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_dimms(server_name, server_info):
    "get dimms info"
    server_info["DIMMS"] = []
    enabled_dimms = 0
    dimms_enpoint = "/redfish/v1/systems/1/Memory/"
    dimms_endpoints, result = get_redfish(dimms_enpoint, server_info)

    for dimm in dimms_endpoints["Members"]:
        endpoint = dimm["@odata.id"]
        response, status_code = get_redfish(endpoint, server_info)
        dimm_name = endpoint.split("/")[-2]
        if response["Status"]["State"] == "Enabled":
            enabled_dimms += 1
            slot = f"{dimm_name} DIMM Check"
            data = f'PROC: {dimm_name} SIZE: {response["CapacityMiB"]} PN: {response["PartNumber"]} '
            server_info["DIMMS"].append(f"{slot},: {data}")
    server_info["DIMMS"].append(f"Memory DIMM Count, {enabled_dimms}")

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_disks(server_name, server_info):
    "get disks info"
    controllers_endpoints = f"/redfish/v1/systems/1/Storage"
    storage, status_code = get_redfish(controllers_endpoints, server_info)
    controllers = storage["Members"]
    server_info["DISKS"] = []

    for index, controller in enumerate(controllers):
        base_controller_endpoint = controller["@odata.id"]
        controller_endpoint = f"{base_controller_endpoint}/Controllers/0"
        controller_info, _ = get_redfish(controller_endpoint, server_info)
        disk_info = [
            f"Smart Array:, {index}",
            f'Smart Storage Array Model Number, {controller_info["Model"]}',
            f'Smart Storage Array Serial Number, {controller_info["SerialNumber"]}',
            f'Smart Storage Array FW Revision, {controller_info["FirmwareVersion"]}',
            f'Smart Storage Array Status, {controller_info["Status"]["Health"]}',
            f'Smart Storage Array Slot, {controller_info["Location"]["PartLocation"]["ServiceLabel"]}',
        ]
        server_info["DISKS"] += disk_info

        raw_constroller, _ = get_redfish(base_controller_endpoint, server_info)
        drives = raw_constroller["Drives"]
        for drive in drives:
            drive_endpoint = drive["@odata.id"]
            drive_info, status = get_redfish(drive_endpoint, server_info)
            if status == 200:
                log = [
                    f'Disk Serial Number,  {drive_info["SerialNumber"]}',
                    f'Disk Firmware Revision, {drive_info["Revision"]}',
                    f'Disk Model TYPE, {drive_info["Model"]}',
                    f'Disk Size (Bytes), {drive_info["CapacityBytes"]}',
                    f'Disk Location, {drive_info["PhysicalLocation"]["PartLocation"]["ServiceLabel"]}',
                    f'Disk Status, {drive_info["Status"]["Health"]}',
                    f'Disk Interface Type, {drive_info["Protocol"]}',
                    f'Disk MediaType, {drive_info["MediaType"]}',
                ]

                try:
                    log.append(
                        f'Disk Current Temperature, {drive_info["Oem"]["Hpe"]["CurrentTemperatureCeslius"]}'
                    )
                except KeyError:
                    pass

                server_info["DISKS"] += log

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_network(server_name, server_info):
    "get network adapters info"
    server_info["NICS"] = []
    nics_enpoint = f"/redfish/v1/Chassis/1/NetworkAdapters/"
    raw_adapters, status_code = get_redfish(nics_enpoint, server_info)
    adapters = raw_adapters["Members"]
    for i, nic in enumerate(adapters):
        nic_endpoint = nic["@odata.id"]
        nic_info, _ = get_redfish(nic_endpoint, server_info)
        nic_log = [
            f"NIC, {i+1}" f'NIC Type, {nic_info["Model"]}',
            f'Firmware Version, {nic_info["Controllers"][0]["FirmwarePackageVersion"]}',
            f'NIC PartNumber, {nic_info["PartNumber"]}',
            f'NIC Serial Number, {nic_info["SerialNumber"]}',
        ]

        server_info["NICS"] += nic_log
        ports_endpoint = f"{nic_endpoint}Ports"
        raw_ports, _ = get_redfish(ports_endpoint, server_info)
        for port in raw_ports["Members"]:
            port_endpoint = port["@odata.id"]
            port_info, _ = get_redfish(port_endpoint, server_info)
            port = [
                f'Port {port_info["Id"]} Ipv4, {port_info["Ethernet"]["LLDPTransmit"]["ManagementAddressIPv4"]}',
                f'Port {port_info["Id"]} MAC, {port_info["Ethernet"]["AssociatedMACAddresses"][0]}',
            ]

            server_info["NICS"] += port

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_fw(server_name, server_info):
    "get fw info for main components"
    server_info["FW"] = []
    fws_enpoint = "/redfish/v1/UpdateService/FirmwareInventory/"
    raw_fws, status_code = get_redfish(fws_enpoint, server_info)
    for fw in raw_fws["Members"]:
        fw_endpoint = fw["@odata.id"]
        fw_info, _ = get_redfish(fw_endpoint, server_info)
        server_info["FW"].append(
            f'FW {fw_info["Id"]} {fw_info["Name"]}, {fw_info["Version"]}'
        )

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_pci(server_name, server_info):
    "get pci info for main components"
    server_info["PCI"] = []
    pcis_enpoint = "/redfish/v1/Chassis/1/Devices/"
    raw_pci, status_code = get_redfish(pcis_enpoint, server_info)
    for pci in raw_pci["Members"]:
        pci_endpoint = pci["@odata.id"]
        pci_info, _ = get_redfish(pci_endpoint, server_info)

        log = [
            f'PCI Device:, {pci_info["Id"]}',
            f'Name:,  {pci_info["Name"]}',
            f'Firmware Version: {pci_info["Name"]}',
            f'Slot:, {pci_info["Location"]}',
            f'Part Number:, {pci_info["PartNumber"]}',
            f'Product Part Number:,  {pci_info["ProductPartNumber"]}',
            f'Serial Number:, {pci_info["SerialNumber"]}',
        ]

        if pci_info["Status"]["State"] == "Enabled":
            log.append(f'Health:, {pci_info["Status"]["Health"]}')

        server_info["PCI"] += log

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def get_psu(server_name, server_info):
    "get psus info"
    server_info["PSUS"] = []
    psus_enpoint = "/redfish/v1/Chassis/1/Power/"
    raw_psus, status_code = get_redfish(psus_enpoint, server_info)

    for psu in raw_psus["PowerSupplies"]:
        id = psu["MemberId"]
        log = [
            f'Power Supply {id} Product Name, {psu["Name"]}',
            f'Power Supply {id} Capacity, {psu["PowerCapacityWatts"]}',
            f'Power Supply {id} Serial Number, {psu["SerialNumber"]}',
            f'Power Supply {id} Model Number, {psu["Model"]}',
            f'Power Supply {id} Spare Model Number, {psu["SparePartNumber"]}',
            f'Power Supply {id} Firmware Version, {psu["FirmwareVersion"]}',
        ]
        if psu["Status"]["State"] == "Enabled":
            log.append(f'Power Supply {id} Health State, {psu["Status"]["Health"]}')

        server_info["PSUS"] += log

    return_code = 0 if status_code == 200 else 1
    return server_name, return_code, server_info, status_code


def print_csv(servers, lo):
    """prints grabbed data into {LO}.csv"""

    with open(f"./log/{lo}/datacollection_{lo}.csv", "w") as csv:
        top_header = [
            f"Purchase Order, ",
            f"Sales Order, {lo}",
        ]
        csv.writelines("\n".join(top_header) + "\n")

        sorted_by_ul = dict(sorted(servers.items(), key=lambda x: x[1]["UL"]))

        for _, server_info in sorted_by_ul.items():

            header = [f':{server_info["UL"]}', f'Racked Location, {server_info["UL"]}']

            encl = server_info["ENCLOSURE"]
            ilo = server_info["ILO_INFO"]
            cpu = server_info["CPU_BIOS"]
            dimms = server_info["DIMMS"]
            disk = server_info["DISKS"]
            nic = server_info["NICS"]
            fw = server_info["FW"]
            pci = server_info["PCI"]
            psus = server_info["PSUS"]

            csv.writelines("\n".join(header) + "\n")
            csv.writelines(
                "\n".join(
                    itertools.chain(encl, ilo, cpu, dimms, disk, nic, fw, pci, psus)
                )
            )


def print_data_excel(servers, lo):
    """prints data into datacollection-to-excel.txt"""

    with open(f"./log/{lo}/datacollection_{lo}-to-excel.txt", "w") as file:
        top_header = [
            f"Purchase Order, ",
            f"Sales Order, {lo}",
        ]

        file.writelines("\n".join(top_header) + "\n")

        for key in sorted(servers.keys()):
            server_info = servers[key]
            file.write(f'\n:{server_info["UL"]}\n')

            model, pn, _ = server_info["ENCLOSURE"]
            model = model.split(",")[-1]
            pn = pn.split(",")[-1].strip()
            sn = server_info["DATA"]["SSN"]

            encl = "\t".join([pn, "N/A", model, sn])

            bios_fw, uuid, _, _, _ = server_info["CPU_BIOS"]
            bios_fw = bios_fw.split(",")[-1]
            uuid = uuid.split(",")[-1]

            ilo_fw = server_info["ILO_INFO"][1]
            ilo_fw = ilo_fw.split(",")[-1]

            entitlement = server_info["DATA"]["LICENSES"][0]["ENTITLEMENT"]
            ilo_key = server_info["DATA"]["LICENSES"][0]["KEY"]
            password = f'{server_info["USER"]}/{server_info["DATA"]["ILO_PASSWORD"]}'
            ilo_version = server_info["ILO_INFO"][1].split(" ")[-1]
            ilo_mac = server_info["DATA"]["ILO_MAC"]
            mode = "DHCP"

            cards = []

            for card in server_info["NICS"]:
                if "MAC" in card:
                    mac = card.split(",")[-1].strip()
                    cards.append(mac)

            data = "\t".join(
                [
                    uuid,
                    entitlement,
                    ilo_key,
                    password,
                    mode,
                    ilo_version,
                    ilo_mac,
                    *cards,
                ]
            )

            line = encl + "\t" + data + "\n"
            file.write(line)


if __name__ == "__main__":
    # ping all servers
    servers = get_servers()

    print(INFO_PREFIX + "Pinging servers." + POSTFIX)
    handle_multiproc(servers, ping_server)

    cont = input("Do you want to proceed? [y/n]: ")
    if cont in ["n", "N", "no", "NO"]:
        print("Canceling execution.")
        exit(1)

    print(INFO_PREFIX + "\nGetting LO number." + POSTFIX)
    LO = get_lo(servers)
    if not LO:
        print("Failed to get LO. Canceling execution.")
        exit(1)

    lo_logs = f"{DATACOLLECTION_LOG}{LO}"
    if os.path.exists(lo_logs):
        print(f"Folder {lo_logs} already exist.")
    else:
        print(f"Creating /data/sfng/log/{LO} directory")
        os.mkdir(lo_logs)

    print(INFO_PREFIX + "\nGetting server info from polaris." + POSTFIX)
    handle_multiproc(servers, get_polaris_info)

    print(INFO_PREFIX + "\nGetting enclosure info." + POSTFIX)
    handle_multiproc(servers, get_enclosure)

    print(INFO_PREFIX + "\nGetting ilo info." + POSTFIX)
    handle_multiproc(servers, get_ilo)

    print(INFO_PREFIX + "\nGetting bios/cpu info." + POSTFIX)
    handle_multiproc(servers, get_bios_cpu)

    print(INFO_PREFIX + "\nGetting drive controllers info" + POSTFIX)
    handle_multiproc(servers, get_disks)

    print(INFO_PREFIX + "\nGetting network adapters info" + POSTFIX)
    handle_multiproc(servers, get_network)

    print(INFO_PREFIX + "\nGetting fw info for the main components" + POSTFIX)
    handle_multiproc(servers, get_fw)

    print(INFO_PREFIX + "\nGetting pci info" + POSTFIX)
    handle_multiproc(servers, get_pci)

    print(INFO_PREFIX + "\nGetting psu info" + POSTFIX)
    handle_multiproc(servers, get_psu)

    print(INFO_PREFIX + "\nGetting memory info." + POSTFIX)
    handle_multiproc(servers, get_dimms)
    # print(servers)
    print(
        f"\nWriting data logs into {MIRECEK_PANTOFLE}./log/{LO}/datacollection_{LO}.csv{POSTFIX}"
    )
    print_csv(servers, LO)

    print(
        f"\nWriting data to {MIRECEK_PANTOFLE}./log/{LO}/datacollection_{LO}-to-excel.txt{POSTFIX}"
    )
    print_data_excel(servers, LO)
