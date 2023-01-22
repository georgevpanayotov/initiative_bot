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
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    global rounds

    if len(message.embeds) > 0:
        embed = message.embeds[0]

        matchInitiative = re.compile("Initiative\([+-]?(\d*)\)")

        if matchInitiative.match(embed.title) is not None:
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

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
                currentRound.maybeAdmin = message.author.id
                await message.channel.send("No admin found. Are you the admin?")
            else:
                everyone = currentRound.context.everyoneId()
                await message.channel.send(f"<@&{everyone}> should roll initiative.")
        elif message.content == "/initiative yes":
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            if currentRound.maybeAdmin is None and currentRound.maybeAdmin == message.author.id:
                currentRound.maybeAdmin = None
                currentRound.context.setAdmin(message.author.id)
            else:
                await message.channel.send(f"I didn't ask you!")
        elif message.content.startswith("/initiative I am"):
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            parts = message.content.split(" ")
            characterKey = parts[3].strip().lower()

            userId = message.author.id

            print(f"{characterKey} is {userId}")
            currentRound.context.setCharacter(userId, characterKey)
        elif message.content.startswith("/initiative advantage"):
            updateSecondRoll(message, SecondRoll.ADVANTAGE)
        elif message.content.startswith("/initiative disadvantage"):
            updateSecondRoll(message, SecondRoll.DISADVANTAGE)
        elif message.content == "/initiative get":
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            if message.author.id != currentRound.context.admin():
                await message.channel.send("Only admin can do that.")
                return

            response = ""
            for i, roll in enumerate(sorted(currentRound.playerRolls.values(),
                                            key = lambda roll: roll.value,
                                            reverse = True)):
                response = response + roll.name + " got " + str(roll.value)
                if i != len(currentRound.playerRolls) - 1:
                    response = response + "\n"

            del rounds[message.channel.id]

            if len(response) == 0:
                return
            await message.channel.send(response)


def handleRoll(currentRound, embed, number):
    characterName = embed.author.name
    characterKey = characterName.split(" ")[0].strip().lower()

    if not characterKey in currentRound.playerRolls:
        currentRound.playerRolls[characterKey] = Roll(characterName, number)
        print(f"Roll: {number} for {characterName}")
    else:
        roll = currentRound.playerRolls[characterKey]
        if roll.secondRoll is None:
            print(f"Rejected Roll: {number} for {characterName}")
        elif roll.secondRoll == SecondRoll.COMPLETED:
            print(f"Rejected Second Roll: {number} for {characterName}")
        else:
            if roll.secondRoll == SecondRoll.ADVANTAGE:
                if number > roll.value:
                    roll.value = number
                    print(f"Updated roll: {number} for {characterName} due to advantage")
            elif roll.secondRoll == SecondRoll.DISADVANTAGE:
                if number < roll.value:
                    roll.value = number
                    print(f"Updated roll: {number} for {characterName} due to disadvantage")
            roll.secondRoll = SecondRoll.COMPLETED


def getCurrentRound(message):
    if not message.channel.id in rounds:
        print("Channel not currently rolling.")
        return None

    return rounds[message.channel.id]


def updateSecondRoll(message, secondRoll):
    currentRound = getCurrentRound(message)
    if currentRound is None:
        return

    userId = message.author.id
    characterKey = currentRound.context.getCharacter(userId)

    if characterKey is None:
        print(f"No character for {userId}.")
        return

    if not characterKey in currentRound.playerRolls:
        print(f"No roll for {characterKey} yet")
        return

    roll = currentRound.playerRolls[characterKey]

    if roll.secondRoll == SecondRoll.COMPLETED:
        print(f"Already did second roll for {roll.name}")
        return

    roll.secondRoll = secondRoll


with open('auth/token', mode='r') as tokenFile:
    client.run(tokenFile.read())
