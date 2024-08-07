from sys import argv
array = []

with open("input_1000_100.txt", "r") as file:
    for line in file.readlines():
        line = line.rstrip()
        tmp = (line.split(" "))
        tmp = tmp[1:]
        tmp = [int(i) for i in tmp]
        array.append(tmp)

#for i in range(len(array)):
#    print(i, array[i])
#    print()

n = int(argv[1])
m = int(argv[2])


print(n, m)

print(array[n])
print(array[m])
result = []

for i in range(1, 101):
    tmp = array[n].index(i)
    print(tmp)
    result.append(array[m][tmp])
print(result)

count = 0

for i in range(len(result)-1):
    for j in range(i + 1, len(result)):
        if result[i] > result[j]:
            print(i + 1, j + 1)
            count += 1
print(count)
