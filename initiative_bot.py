#!/usr/bin/python3

import discord
import os
import re

from discord import Intents
from parsing import parseNumbers
from roll_model import Roll
from roll_model import RollingRound
from roll_model import SecondRoll

intents = Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents = intents)

rounds = {}

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    global rounds

    if len(message.embeds) > 0:
        embed = message.embeds[0]

        matchInitiative = re.compile("Initiative\([+-]?(\d*)\)")

        if matchInitiative.match(embed.title) is not None:
            if not message.channel.id in rounds:
                print("Channel not currently rolling.")
                return

            currentRound = rounds[message.channel.id]

            for field in embed.fields:
                number = parseNumbers(field.name)

                if number is None:
                    # No roll here ignore the rest of this field.
                    continue

                handleRoll(currentRound, embed, number)

    else:
        if message.content == "/initiative":
            # Initialize a rolling round.
            currentRound = RollingRound(message.channel.id)
            rounds[message.channel.id] = currentRound

            if currentRound.context.admin() is None:
                currentRound.mommyId = message.author.id
                await message.channel.send("No admin found. Are you my mommy?")
            else:
                everyone = currentRound.context.everyoneId()
                await message.channel.send(f"<@&{everyone}> should roll initiative.")
        elif message.content == "/initiative yes":
            if not message.channel.id in rounds:
                print("Channel not currently rolling.")
                return

            currentRound = rounds[message.channel.id]
            if currentRound.mommyId is None:
                return

            if currentRound.mommyId == message.author.id:
                currentRound.mommyId = None
                currentRound.context.setAdmin(message.author.id)
            else:
                await message.channel.send(f"I didn't ask you!")
        elif message.content.startswith("/initiative I am"):
            if not message.channel.id in rounds:
                print("Channel not currently rolling.")
                return

            currentRound = rounds[message.channel.id]
            parts = message.content.split(" ")
            # TODO: tolower character
            print(parts[3] + " is " + message.author.id)
            currentRound.context.setCharacter(message.author.id, parts[3])
        elif message.content.startswith("/initiative advantage"):
            if not message.author.id in currentRound.rolls:
                print("No roll for " + message.author.id + " yet")
                return
            # TODO: Get character name here:
            roll = currentRound.rolls[message.author.id]
            roll.secondRoll = SecondRoll.ADVANTAGE
        elif message.content.startswith("/initiative disadvantage"):
            if not message.author.id in currentRound.rolls:
                print("No roll for " + message.author.id + " yet")
                return
            # TODO: Get character name here:
            roll = currentRound.rolls[message.author.id]
            roll.secondRoll = SecondRoll.DISADVANTAGE
        elif message.content == "/initiative get":
            if not message.channel.id in rounds:
                print("Channel not currently rolling.")
                return

            currentRound = rounds[message.channel.id]
            if message.author.id != currentRound.context.admin():
                await message.channel.send("Only admin can do that.")
                return

            response = ""
            for i, roll in enumerate(sorted(currentRound.rolls.values(), key = lambda roll: roll.value, reverse = True)):
                response = response + roll.name + " got " + str(roll.value)
                if i != len(currentRound.rolls) - 1:
                    response = response + "\n"

            del rounds[message.channel.id]

            if len(response) == 0:
                return
            await message.channel.send(response)


def handleRoll(currentRound, embed, number):
    # TODO: Just first name of character. Tolower()
    author = embed.author.name

    if not author in currentRound.rolls:
        currentRound.rolls[author] = Roll(author, int(number))
        print("Roll: " + number + " for " + author)
    else:
        roll = currentRound.rolls[author]
        if roll.secondRoll is None:
            print("Rejected Roll: " + str(number) + " for " + author)
        elif roll.secondRoll == SecondRoll.ADVANTAGE:
            if number > roll.value:
                roll.value = number
                print("Updated roll: " + str(number) + " for " + author + " due to advantage")
        elif roll.secondRoll == SecondRoll.DISADVANTAGE:
            if number < roll.value:
                roll.value = number
                print("Updated roll: " + str(number) + " for " + author + " due to disadvantage")


with open('auth/token', mode='r') as tokenFile:
    client.run(tokenFile.read())
