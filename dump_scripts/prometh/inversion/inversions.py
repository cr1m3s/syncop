al = [1, 5, 4, 3, 2]
arr = [5, 3, 2, 1, 4]

#bo = [5, 4, 1, 2, 3]

# 3 1 2 4 5
# 3 1 2 4 5
#
count = 0

for i in range(len(al)-1):
    for j in range(i + 1, len(bo)):
        if bo[i] > bo[j]:
            print(i + 1, j + 1)
            count += 1

print(count)
