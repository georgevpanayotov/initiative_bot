#!/usr/bin/python3

import re

from logging_config import getLogger

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
    "keycap_ten" : "10",
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
                getLogger().error("Unmatched ':'")
                return None

            while rollTitle[i] != ":":
                number = number + rollTitle[i]
                i = i + 1
                if i >= len(rollTitle):
                    getLogger().error("Unmatched ':'")
                    return None

            i = i + 1
            if i >= len(rollTitle):
                done = True
            numStr = numStr + NUMBER_MAP[number]
        else:
            done = True

    return int(numStr) if len(numStr) > 0 else None


def parseCrossedOut(rollTitle):
    matchCrossedOut = re.compile("~~(\d*)~~")
    matches = matchCrossedOut.match(rollTitle)
    if matches is None:
        return None
    else:
        return int(matches.group(1))


def parseEither(rollTitle):
    number = parseNumbers(rollTitle)
    if number is not None:
        return number

    return parseCrossedOut(rollTitle)
