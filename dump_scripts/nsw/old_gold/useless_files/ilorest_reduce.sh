#/usr/bin/sh

cat ilorest_params | while read param
do
	result=$(grep "$param"  ilorest_full | uniq -c)
	echo $result
done
