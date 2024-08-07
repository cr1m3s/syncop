#!/usr/bin/env python3

from sys import argv

filename = argv[1]

array = []

with open(filename) as file:
    for line in file.readlines():
        array.append(int(line.rstrip()))

array = array[1:]
array.sort()
arrayLen = len(array)
med = array[int(arrayLen/2)]
medians = [array[med], array[med+1]]

print(f"{med}, {med + 1}, {medians[0]}, {medians[1]}")


