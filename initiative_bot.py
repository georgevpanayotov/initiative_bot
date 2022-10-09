#!/usr/bin/python3

import discord
import os
import re

from discord import Intents

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

intents = Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents = intents)

class Roll:
    def __init__(self, name, value):
        self.name = name
        self.value = value

rolling = False
rolls = {}

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    global rolls

    if len(message.embeds) > 0:
        embed = message.embeds[0]

        matchInitiative = re.compile("Initiative\([+-]?(\d*)\)")

        if matchInitiative.match(embed.title) is not None:
            for field in embed.fields:
                number = parseNumbers(field.name)
                if number is not None and not embed.author.name in rolls:
                    rolls[embed.author.name] = Roll(embed.author.name, int(number))
                    print("Roll: " + number + " for " + embed.author.name)
                else:
                    print("Rejected Roll: " + field.name + " for " + embed.author.name)
    else:
        if message.content == "/initiative":
            rolls = {}
            rolling = True
            await message.channel.send("Everyone should roll initiative.")
        if message.content == "/get_initiative":
            response = ""
            for i, roll in enumerate(sorted(rolls.values(), key = lambda roll: roll.value, reverse = True)):
                response = response + roll.name + " got " + str(roll.value)
                if i != len(rolls) - 1:
                    response = response + "\n"

            rolls = {}
            rolling = False

            if len(response) == 0:
                return
            await message.channel.send(response)



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

with open('auth/token', mode='r') as tokenFile:
    client.run(tokenFile.read())
