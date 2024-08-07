#!/usr/bin/env bash

#for i in $( cat ip.txt ); do
#	echo "$i"
#	ilorest flashfwpkg 26_37_1700-MCX631102AS-ADA_Ax.pldm.fwpkg --url "$i" -u admin -p admin -p admin --forceupload --logout &
#done


for i in $( cat ip.txt ); do
	echo "$i"
	#ilorest flashfwpkg ilo6_156.fwpkg --url "$i" -u admin -p admin -p admin --forceupload --logout &

	ilorest flashfwpkg U54_2.12_12_13_2023.fwpkg --url "$i" -u admin -p admin --forceupload --logout &
	#ilorest flashfwpkg SC_U54_ME_06.01.04.005.0.fwpkg --url "$i" -u admin -p admin -p admin --forceupload --logout &
done

#for i in $( cat ip.txt ); do
#	echo "$i"
#	ilorest flashfwpkg HPE_MR216i-o_Gen11_52.24.3-4948_B.fwpkg --url "$i" -u admin -p admin -p admin --forceupload --logout &
#done

#for i in $( cat ip.txt ); do
#	echo "$i"
#	ilorest flashfwpkg "$1" --url "$i" -u admin -p admin --forceupload --logout &
#done

#grep CZ /etc/ansible/hosts | while read -r line; do
#	#echo $line
#	ip=$( echo $line | cut -d " " -f 2 | cut -d "=" -f 2 )
#	pswd=$( echo $line | cut -d  " " -f 3 | cut -d "=" -f 2) 
#	echo ilorest flashfwpkg "$1" --url "$ip" -u Administrator -p "$pswd" --forceupload --logout
#	ilorest flashfwpkg "$1" --url "$ip" -u Administrator -p "$pswd" --forceupload --logout &
#
#	#echo ilorest virtualmedia 2 insert="$1" --url "$ip" -u admin -p admin 
#done
