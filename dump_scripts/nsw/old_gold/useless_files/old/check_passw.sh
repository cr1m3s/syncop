#/usr/bin/sh

grep CZ uloc.txt | while read server
do
	sn=$(echo $server | awk '{print $1}')
	pswd=$(perl /data/sfng/get_pwd_lic.pl --sn=$sn | awk '{print $1}')
	echo "$server	passwd : $pswd"
done
