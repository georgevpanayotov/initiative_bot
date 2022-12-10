#!/usr/bin/python3

NUMBER_MAP = {
    "one" : "1",
    "two" : "2",
    "three" : "3",
    "four" : "4",
    "five" : "5",
    "six" : "6",
    "seven" : "7",
    "eight" : "8",
    "nine" : "9",
    "zero" : "0",
}

def parseNumbers(rollTitle):
    numStr = ""
    done = False
    i = 0
    while not done:
        if rollTitle[i] == ":":
            number = ""
            i = i + 1
            if i >= len(rollTitle):
                print("Error: unmatched ':'")
                return None

            while rollTitle[i] != ":":
                number = number + rollTitle[i]
                i = i + 1
                if i >= len(rollTitle):
                    print("Error: unmatched ':'")
                    return None

            i = i + 1
            if i >= len(rollTitle):
                done = True
            numStr = numStr + NUMBER_MAP[number]
        else:
            done = True

    return numStr if len(numStr) > 0 else None
