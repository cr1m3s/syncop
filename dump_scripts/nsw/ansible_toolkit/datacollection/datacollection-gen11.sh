#!/bin/bash
count=$(grep CZ /data/sfng/ipmapping |wc -l)
i=1

# Test all IP addresses with ping
echo -e "\n\n================"
echo -e "¦ ping iLO IPs ¦"
echo -e "================"
grep CZ ipmapping | while read line
do
    ServerSN=$(echo $line | awk '{print $1}')
    ServerIP=$(echo $line | awk '{print $2}' | tr -d "\n" | tr -d "\r")
	echo -n ${ServerSN} ${ServerIP}
    ping -c1 ${ServerIP} > /dev/null 2>&1
    if [ $? -eq 0 ]; then
    echo " - Server OK"
    else
    echo " -- NO reply --"
    fi
done
echo -e "\n"
read -p "All OK? Press any key to continue ... or CTRL+C to stop" -n1 -s
echo -e "\n"

srv_data=`perl /data/sfng/get_pwd_lic.pl --sn=$(ls /data/log/NokiaNSW/*.json | head -1 | awk -F "_" '{print substr($3,1,10)}')`
HPON=$(echo $srv_data | awk '{print $3}')

# Create folder for whole rack based on HPON
if [[ ! -d /data/sfng/log/${HPON} ]]; then
    mkdir -p /data/sfng/log/${HPON}
fi

# get all SNs and target IPs from 'ipmapping' file, get iLO password, License, HPE Sales Order nr. and Parent (Rack SN) from SFC, get FW version from iLO
grep CZ ipmapping | while read line
do
    ServerSN=$(echo $line | awk '{print $1}')
    ServerIP=$(echo $line | awk '{print $2}' | tr -d "\n" | tr -d "\r")
    Location=$(echo $line | awk '{print $3}' | tr -d "\n" | tr -d "\r")
    echo -e "\n== Unit $i / $count == ${Location}:${ServerSN} =="
	echo -ne "[ 5%] SFC data                      \r"
    ((i++))
  # ilo_IP=`dhcp-lease-list --lease /var/lib/dhcpd/dhcpd.leases | grep ${ServerSN}|awk '{print $2}'`
    ilo_data=`perl /data/sfng/get_pwd_lic.pl --sn=${ServerSN}`
    iloPassAdministrator=$(echo $ilo_data |awk '{print $1}')
    ilo_lic=$(echo $ilo_data | awk '{print $2}')
    HPE_SO=$(echo $ilo_data | awk '{print $3}')
    ENTITLEMENT=$(echo $ilo_data | awk '{print $4}')
    PARENT=$(echo $ilo_data | awk '{print $5}')
#debug:
    # iloPassAdministrator=Nsah2damsj@1lO!
    # HPE_SO=TEST
	
# get_pwd_lic.pl -> output:
# 1= $password 
# 2= $licences[$i]->{KEY} 
# 3= $SO
# 4= $licences[$i]->{ENTITLEMENT}
# 5= $PARENT  

# Create folder for whole rack based on HPE_SO
if [[ ! -d /data/sfng/log/${HPE_SO} ]]; then
    mkdir -p /data/sfng/log/${HPE_SO}
fi
# Create logfile
if [[ ! -f /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv ]]; then
	echo "Purchase Order," > /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo "Sales Order,${HPE_SO}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
fi

echo ":${Location}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
echo "Racked Location,${Location}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv

# Enclosure
	echo -ne "[10%] Enclosure details\r"
enclosure=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/Chassis/1/ -u Administrator:${iloPassAdministrator} --insecure)
	echo ${enclosure}| jq -r '"Enclosure Type," + .Model' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${enclosure}| jq -r '"PN from OEM," + .SKU' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${enclosure}| jq -r '"SN from OEM," + .SerialNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	
# iLO DATA
	echo -ne "[20%] iLO data                      \r"
	echo "iLO MAC Address,"$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/managers/1/EthernetInterfaces/1/ -u Administrator:${iloPassAdministrator} --insecure | jq -r '.MACAddress') >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo "iLO FW Version,"$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/Managers/1/ -u Administrator:${iloPassAdministrator} --insecure | jq -r '.Oem.Hpe.Firmware.Current.VersionString'| awk '{print $3}') >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo "iLO Advanced License Key,${ilo_lic}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo "iLO OEM Password,${iloPassAdministrator}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	
# BIOS and CPUs
	echo -ne "[30%] BIOS and CPUs                      \r"
	bios=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/ -u Administrator:${iloPassAdministrator} --insecure)
	echo ${bios}| jq -r '"BIOS FW version," + .BiosVersion' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${bios}| jq -r '"UUID," + .UUID' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${bios}| jq -r '"CPU Count," + (.ProcessorSummary.Count|tostring)' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${bios}| jq -r '"CPU Type," + .ProcessorSummary.Model' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	
# Memory
	echo -ne "[40%] Memory slots                      \r"
mems=0
for proc in {1..2}
do
	for dimm in {1..16}
	do
		dimm_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/Memory/proc${proc}dimm${dimm} -u Administrator:${iloPassAdministrator} --insecure)
		if [[ "$(echo ${dimm_detail} | jq -r '.CapacityMiB')" -ne 0 ]] && [ $dimm  -lt 10 ]
		then 
			echo -n "P${proc}D${dimm}  DIMM Check,PROC: ${proc} DIMM: ${dimm} " >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv && echo ${dimm_detail} | jq -r '" SIZE: " + (.CapacityMiB|tostring) + "MiB PN: " + .PartNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			((mems++))
		elif [[ "$(echo ${dimm_detail} | jq -r '.CapacityMiB')" -ne 0 ]] 
			then
			echo -n "P${proc}D${dimm} DIMM Check,PROC: ${proc} DIMM: ${dimm} " >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv && echo ${dimm_detail} | jq -r '"SIZE: " + (.CapacityMiB|tostring) + "MiB PN: " + .PartNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			((mems++))
			# split for proper formatting of single- and double-digit entries
		fi
	done
done
echo "Memory DIMM Count,${mems}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
echo "RAM Memory Size,"$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/ -u Administrator:${iloPassAdministrator} --insecure | jq -r '.MemorySummary.TotalSystemMemoryGiB')"GB" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	
# Storage - Smart Array
# - Only physical drives as we don't create any LDs
# - Add cycle for HBA if present:
# 		HBA=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/SmartStorage/HostBusAdapters -u Administrator:${iloPassAdministrator} --insecure | jq -r '."Members@odata.count"')
# 		echo "HBA: ${HBA}"
	echo -ne "[50%] Storage controllers                      \r"

SA_count=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/Storage -u Admin:admin --insecure |jq -r '."Members@odata.count"')
SA_list=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/Storage -u Admin:admin --insecure |jq -r '."Members"')

j=1
if [ ${SA_count} -ne 0 ]; then
for smartarray in $( echo -e "${SA_list}" | grep -i odata  | cut -d: -f2 |sed 's/"//g' |sed 's/ //g')
	do

	echo "SmartArray: ${j}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	sa_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}${smartarray}/Controllers/0 -u Admin:admin --insecure)
	echo ${sa_detail}| jq -r '"Smart Storage Array Model Number," + .Model' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${sa_detail}| jq -r '"Smart Storage Array Serial Number," + .SerialNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${sa_detail}| jq -r '"Smart Storage Array FW Revision," + .FirmwareVersion' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	#echo ${sa_detail}| jq -r '"Smart Storage Array HW Revision," + .HardwareRevision' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${sa_detail}| jq -r '"Smart Storage Array Status," + .Status.Health' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	echo ${sa_detail}| jq -r '"Smart Storage Array Slot," + .Location.ServiceLabel' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	((j++))
	
# Disks
# TBD: move Disk listing into the SmartArray loop

	disk_list=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}${smartarray} -u Admin:admin --insecure | jq -r '.Drives')
	disk_count=1
	
	for disk in  $( echo -e "${disk_list}" | grep -i odata | sed 's/ //g' | sed 's/"//g' | cut -d: -f2 ); 
	do
        	disk_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}$disk -u Admin:admin --insecure)
			echo "Disk ${disk_count}:" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			((disk_count++))
			echo ${disk_detail}|jq -r '"Disk Serial Number," + .SerialNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk Firmware Revision," + .Revision' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk Model TYPE," + .Model' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk Size (Bytes)," + (.CapacityBytes|tostring)' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk Location," + .PhysicalLocation.PartLocation.ServiceLabel' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk Status," + .Status.Health' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk Interface Type," + .Protocol' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk MediaType," + .MediaType' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${disk_detail}|jq -r '"Disk Current Temperature," + (.Oem.Hpe.CurrentTemperatureCelsius|tostring)' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			#echo ${disk_detail}|jq -r '"Disk Maximum Temperature," + (.MaximumTemperatureCelsius|tostring)' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			#echo ${disk_detail}|jq -r '"Disk Physical Interface Transfer Rate (Mbps)," + (.InterfaceSpeedMbps|tostring)' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			#echo ${disk_detail}|jq -r '"Disk Carrier Application Version," + .CarrierApplicationVersion' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	done
	done
fi	

# Network adapters
	echo -ne "[70%] Network adapters                      \r"
	nic_list=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/Systems/1/Ethernewinterfaces/ -u Administrator:${iloPassAdministrator} --insecure | jq -r '.Members')
	nic_count=1
	for nic in  $( echo -e "${nic_list}" | grep -i odata | sed 's/ //g' | sed 's/"//g' | cut -d: -f2 )
	  do
		nic_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}$nic -u Administrator:${iloPassAdministrator} --insecure)
		echo "NIC ${nic_count}:" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		((nic_count++))
		echo ${nic_detail}|jq -r '"NIC Type," + .Name' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${nic_detail}|jq -r '"Firmware Version," + .Firmware.Current.VersionString' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${nic_detail}|jq -r '"NIC PartNumber," + .PartNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${nic_detail}|jq -r '"NIC Slot," + .StructuredName' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		port_count=$(echo $nic_detail | jq -r '.[]' | grep -c MacAddress)
		for port in  $(seq 1 ${port_count})
		  do
			echo ${nic_detail}| jq -r --argjson nr "$port" '"Port " + ($nr|tostring) + " IPv4," + (.PhysicalPorts[$nr-1].IPv4Addresses|tostring)' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
			echo ${nic_detail} | jq -r --argjson nr "$port" '"Port " + ($nr|tostring) + " MAC Address," + .PhysicalPorts[$nr-1].MacAddress' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		  done
	  done
	
# FW versions
	echo -ne "[75%] Firmware versions                      \r"
	fw_list=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/UpdateService/FirmwareInventory/ -u Administrator:${iloPassAdministrator} --insecure | jq -r '.Members')
	for fw in  $( echo -e "${fw_list}" | grep -i odata | sed 's/ //g' | sed 's/"//g' | cut -d: -f2 )
	  do
		fw_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}$fw -u Administrator:${iloPassAdministrator} --insecure)
		echo ${fw_detail}|jq -r '"FW" + .Id + ": " + .Name + "," + .Version' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	  done
	
# PCI Devices
	echo -ne "[80%] PCI Devices                      \r"
	pci_list=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/Chassis/1/Devices/ -u Administrator:${iloPassAdministrator} --insecure | jq -r '.Members')
	for pci in  $( echo -e "${pci_list}" | grep -i odata | sed 's/ //g' | sed 's/"//g' | cut -d: -f2 )
	  do
		pci_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}$pci -u Administrator:${iloPassAdministrator} --insecure)
		echo ${pci_detail}|jq -r '"PCI Device:," + .Id' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${pci_detail}|jq -r '"Name:," + .Name' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${pci_detail}|jq -r '"Firmware Version:," + .FirmwareVersion.Current.VersionString' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${pci_detail}|jq -r '"Slot:," + .Location' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${pci_detail}|jq -r '"Part Number:," + .PartNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${pci_detail}|jq -r '"Product Part Number:," + .ProductPartNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${pci_detail}|jq -r '"Serial Number:," + .SerialNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${pci_detail}|jq -r '"Health:," + .Status.Health' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		done
	
# Power Supplies
	echo -ne "[85%] Power Supplies                      \r"
	power_supplies=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/Chassis/1/Power -u Administrator:${iloPassAdministrator} --insecure)
	for psu in  {1..2}
	  do
		echo ${power_supplies}|jq -r --argjson ps "$psu" '"Power Supply " + ($ps|tostring) + " Product Name," + .PowerSupplies[$ps-1].Name' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${power_supplies}|jq -r --argjson ps "$psu" '"Power Supply " + ($ps|tostring) + " Capacity," + (.PowerSupplies[$ps-1].PowerCapacityWatts|tostring) + " Watts"' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${power_supplies}|jq -r --argjson ps "$psu" '"Power Supply " + ($ps|tostring) + " Serial Number," + .PowerSupplies[$ps-1].SerialNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${power_supplies}|jq -r --argjson ps "$psu" '"Power Supply " + ($ps|tostring) + " Model Number," + .PowerSupplies[$ps-1].Model' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${power_supplies}|jq -r --argjson ps "$psu" '"Power Supply " + ($ps|tostring) + " Spare Model Number," + .PowerSupplies[$ps-1].SparePartNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${power_supplies}|jq -r --argjson ps "$psu" '"Power Supply " + ($ps|tostring) + " Firmware Version," + .PowerSupplies[$ps-1].FirmwareVersion' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
		echo ${power_supplies}|jq -r --argjson ps "$psu" '"Power Supply " + ($ps|tostring) + " Health State," + .PowerSupplies[$ps-1].Status.Health' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}.csv
	  done

# Data collection formatted for import to Excel (end-customer orders)
	echo -ne "[90%] Excel data collection                 \r"
# Create logfile
if [[ ! -f /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt ]]; then
	echo "Purchase Order," > /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo "Sales Order,${HPE_SO}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
fi

echo -e "\n:${Location}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt

enclosure2=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/Chassis/1/ -u Administrator:${iloPassAdministrator} --insecure)
	echo -n ${enclosure2}| jq -j '.SKU' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne "N/A" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -n ${enclosure2}| jq -j '.Model' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -n ${enclosure2}| jq -j '.SerialNumber' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	
bios2=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/ -u Administrator:${iloPassAdministrator} --insecure)
	echo -n ${bios2}| jq -j '.UUID' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -n ${ENTITLEMENT} >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -n ${ilo_lic} >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne "administrator/${iloPassAdministrator}" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne "DHCP" >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -n $(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/Managers/1/ -u Administrator:${iloPassAdministrator} --insecure | jq -j '.Oem.Hpe.Firmware.Current.VersionString'| awk '{print $3}') >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -n $(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/managers/1/EthernetInterfaces/1/ -u Administrator:${iloPassAdministrator} --insecure | jq -j '.MACAddress') >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
	echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt

# sorted to list LOM first and then adapters in other slots
nic_list_lom=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/systems/1/BaseNetworkAdapters/ -u Administrator:${iloPassAdministrator} --insecure | jq -j '.Members')
	for nic in  $( echo -e "${nic_list_lom}" | grep -i odata | sed 's/ //g' | sed 's/"//g' | cut -d: -f2 )
	  do
		nic_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}$nic -u Administrator:${iloPassAdministrator} --insecure)
		port_count=$(echo $nic_detail | jq -j '.[]' | grep -c MacAddress)
	    if [[ "$(echo -e ${nic_detail} | jq -j '.StructuredName')" =~ "LOM" ]]
			then
			  for port in  $(seq 1 ${port_count})
				do
				echo -n ${nic_detail} | jq -j --argjson nr "$port" '.PhysicalPorts[$nr-1].MacAddress' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
				echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
				done
		fi
	  done

nic_list_slot=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}/redfish/v1/chassis/1/NetworkAdapters/ -u Administrator:${iloPassAdministrator} --insecure | jq -j '.Members')
	for nic in  $( echo -e "${nic_list_slot}" | grep -i odata | sed 's/ //g' | sed 's/"//g' | cut -d: -f2 )
	  do
		nic_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}$nic -u Administrator:${iloPassAdministrator} --insecure)
		port_count=$(echo ${nic_detail} | jq -j '.[]' | grep NetworkPortCount | sed 's/ //g'| cut -d: -f2| sed 's/,//g')
		for port in $(seq 0 $((port_count-1)))
			do
			port_detail=$(curl -s -H "Content-Type: application/json" -X GET https://${ServerIP}${nic}Ports/${port} -u Administrator:${iloPassAdministrator} --insecure)
			echo -n ${port_detail} | jq -j '.Ethernet.AssociatedMACAddresses[0]' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
			echo -ne '\t' >> /data/sfng/log/${HPE_SO}/datacollection_${HPE_SO}-to-excel.txt
			done
	  done

# Data collection of all FW versions for Firmware check
	echo -ne "[95%] Firmware check                 \r"
	echo -e "\n--------------------------------------------------------------------------------" >> /data/sfng/log/${HPE_SO}/FW_check_full.txt
	echo "Firmware check for server: UL: ${Location}, SN: ${ServerSN}, IP: ${ServerIP}" >> /data/sfng/log/${HPE_SO}/FW_check_full.txt
	ilorest serverinfo --firmware --url ${ServerIP} -u admin -p admin >> /data/sfng/log/${HPE_SO}/FW_check_full.txt

echo -ne "[100%] Done                      "
done

# Sort and clean up FW list
echo -e "\n==============="
echo -e "Firmware check:\n"

ilorest_params=("10/25Gb 2P 641SFP28 Adptr" "MCX5" "iLO 5 :" "iLO 6 :" "Intel(R) Eth" "System ROM" "MR216" "MR416" "ConnectX-6")

for param in "${ilorest_params[@]}"
do
	grep "$param" /data/sfng/log/${HPON}/FW_check_full.txt | sort | uniq -c | tee -a /data/sfng/log/${HPON}/FW_check_reduced.txt
done

grep "Nvidia Network Adapter" /data/sfng/log/${HPON}/FW_check_full.txt |awk -F "-" '{print substr($1,1,30) substr($2,20,30) }' | uniq -c |tee -a /data/sfng/log/${HPON}/FW_check_reduced.txt
grep "Mellanox Network Adapter" /data/sfng/log/${HPON}/FW_check_full.txt |awk -F "-" '{print substr($1,1,30) substr($2,20,30) }' | uniq -c |tee -a /data/sfng/log/${HPON}/FW_check_reduced.txt
echo " === Disks in Storage Nodes ===" >> /data/sfng/log/${HPON}/FW_check_reduced.txt
grep "NVMe Drive" /data/sfng/log/${HPON}/FW_check_full.txt | uniq -c |tee -a /data/sfng/log/${HPON}/FW_check_reduced.txt
grep "6G SATA SSD" /data/sfng/log/${HPON}/FW_check_full.txt | uniq -c |tee -a /data/sfng/log/${HPON}/FW_check_reduced.txt

### END ###
