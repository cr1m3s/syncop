#!/usr/bin/env python3
import requests
import json
import sys

sns = []
with open(sys.argv[1], "r") as file:
        for line in file:
            sn = [i for i in line.split("\t") if "CZ" in i]
            sn = sn[0].strip()
            sns.append(sn)

for sn in sns:
    print(f"|{sn}|")

for key in sns:
        request = requests.get(f"https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER={key}")
        if request.status_code == 200:
                tmp = json.loads(request.text)
                
                print(f'{key}\t{tmp["DATA"]["LICENSES"][0]["ENTITLEMENT"]}\t{tmp["DATA"]["LICENSES"][0]["KEY"]}')
        else:
            print(f"Can't get pswd for {key}")
