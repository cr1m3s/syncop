#!/usr/bin/env python3

from sys import argv

counter = 0

def getMediana(array, p, r):
    q = int((p + r) / 2)
    tmp = [array[p], array[q], array[r]]
    tmp.sort()
    mediana = tmp[1]

    if array[p] == tmp[1] :
            array[p] = array[r]
            array[r] = mediana
    elif array[q] == tmp[1]:
        array[q] = array[r]
        array[r] = mediana

    return partition(array, p, r)

def partition(arr, p, r):
    x = arr[r]
    i = p - 1
    global counter
    counter += r - p
    for j in range(p, r):
        if arr[j] <= x:
            i += 1
            (arr[i], arr[j]) =  (arr[j], arr[i])
    (arr[i+1], arr[r]) = (arr[r], arr[i+1])

    return i + 1

def quickSort(array, low, high):
    
    if low < high:
        # firrst element as base:
        # (array[low], array[high]) = (array[high], array[low])
        
        #base case when pivot is the last element:
        #pi = partition(array, low, mediana)

        pi = getMediana(array, low, high)

        quickSort(array, low, pi - 1)
        quickSort(array, pi + 1, high)


if __name__ == "__main__":

    filename = argv[1]
    print(filename)

    inp = []
    with open(filename) as f:
        for line in f.readlines():
            number = int(line.rstrip())
            inp.append(number)
    inp = inp[1:]
    quickSort(inp, 0, len(inp) - 1)
    print(counter)
