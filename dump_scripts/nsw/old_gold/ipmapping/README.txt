ipmapping.py

In order to generate ipmappig put SN+Ulock into ulock.txt file in format:

SN + \t + Ulock into ulock.txt
CZ22420981      U40
CZ22420989      U39
...
CZ224209D4      U1

(copy from exel or must be separated by tab)

./ipmapping.py

Script:
-- restarts dhcp
systemctl restart dhcpd.service  

-- reads list of adresses and creates dictioary where key=SN, value=IP
dhcp-lease-list | grep ILOCZ | awk '{print $2, $3}' 

copy output or redirect into dest file:

// be careful '>' will overwrite previous data
./ipmapping > /data/sfng/ipmapping


ilorest_check.py

takes info from /data/sfng/ipmapping and performs ilorest firmware check on all servers from it
