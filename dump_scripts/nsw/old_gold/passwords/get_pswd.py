#!/usr/bin/env python3
import requests
import json

sns = []
with open("servers.txt", "r") as file:
        for line in file:
                sns.append(line.rstrip())

for sn in sns:
    print(f"|{sn}|")

for key in sns:
        request = requests.get(f"https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER={key}")
        if request.status_code == 200:
                tmp = json.loads(request.text)
                #print(tmp) 
                print(f'{key}\t{tmp["DATA"]["ILO_PASSWORD"]}')
        else:
            print(f"Can't get pswd for {key}")
