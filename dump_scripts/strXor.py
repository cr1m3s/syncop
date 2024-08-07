#!/usr/bin/env python3

from sys import argv

class termColors:
    OKGREEN = '\033[92m'
    OKYELLOW = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def getopts(argv):
    words = []
    for word in argv[1:]:
        words.append(word)
    return words

def printRes(base, word):
    base_len = len(base)

    for i in range(len(word)):
        if i < base_len:
            if base[i] != 0 :
                print(f"{termColors.FAIL}{word[i]}{termColors.ENDC}", end = " ")
            else:
                print(f"{termColors.OKGREEN}{word[i]}{termColors.ENDC}", end = " ")
        else:
            print(f"{termColors.OKYELLOW}{word[i]}{termColors.ENDC}", end = " ")

if __name__ == '__main__':
    words = getopts(argv)
    result = []
    if len(words) != 2:
        print("Usage: enter two words separated by space")
        exit(1)
    else:
        xor_l = min(map(len, words))
        result = [(ord(a) ^ ord(b)) for a, b in zip(words[0][:xor_l], words[1][:xor_l])]
    print(result)
    printRes(result, words[0])
    print()
    printRes(result, words[1])
