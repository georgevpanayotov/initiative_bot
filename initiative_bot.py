#!/usr/bin/python3

import discord
import os
import re

from discord import Intents
from logging_config import configure
from logging_config import getLogger
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
    getLogger().info(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    global rounds

    channelTag = getChannelTag(message.channel)

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

                handleRoll(channelTag, currentRound, embed, number)

    else:
        if message.content == "/initiative":
            # Initialize a rolling round.
            currentRound = RollingRound(channelTag, message.channel.id)
            rounds[message.channel.id] = currentRound

            if currentRound.context.admin() is None:
                currentRound.maybeAdmin = message.author.id
                getLogger().info(f"[{channelTag}] Trying to find admin.")
                await message.channel.send("No admin found. Are you the admin?")
            elif message.author.id == currentRound.context.admin():
                getLogger().info(f"[{channelTag}] Starting round.")
                everyone = currentRound.context.everyoneId()
                await message.channel.send(f"<@&{everyone}> should roll initiative.")
            else:
                getLogger().error(f"[{channelTag}] Non-admin tried to start a round.")
                del rounds[message.channel.id]
                await message.channel.send(f"Only admin can do that.")
        elif message.content == "/initiative yes":
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            if currentRound.maybeAdmin is not None and currentRound.maybeAdmin == message.author.id:
                currentRound.maybeAdmin = None
                currentRound.context.setAdmin(message.author.id)
                getLogger().info(f"[{channelTag}] Found admin.")
            else:
                await message.channel.send(f"I didn't ask you!")
        elif message.content.startswith("/initiative I am"):
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            parts = message.content.split(" ")
            characterKey = parts[3].strip().lower()

            userId = message.author.id

            getLogger().info(f"[{channelTag}] {characterKey} is {message.author.name} ({userId})")
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
                getLogger().error("[{channelTag}] Non admin tried to get summary.")
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
            getLogger().info("[{channelTag}] Summary done.")
            await message.channel.send(response)


def handleRoll(channelTag, currentRound, embed, number):
    characterName = embed.author.name
    characterKey = characterName.split(" ")[0].strip().lower()

    if not characterKey in currentRound.playerRolls:
        currentRound.playerRolls[characterKey] = Roll(characterName, number)
        getLogger().info(f"[{channelTag}] Roll: {number} for {characterName}")
    else:
        roll = currentRound.playerRolls[characterKey]
        if roll.secondRoll is None:
            getLogger().error(f"[{channelTag}] Rejected Roll: {number} for {characterName}")
        elif roll.secondRoll == SecondRoll.COMPLETED:
            getLogger().error(f"[{channelTag}] Rejected Second Roll: {number} for {characterName}")
        else:
            if roll.secondRoll == SecondRoll.ADVANTAGE:
                if number > roll.value:
                    roll.value = number
                    getLogger().info(f"[{channelTag}] Updated roll: {number} for {characterName} due to advantage")
            elif roll.secondRoll == SecondRoll.DISADVANTAGE:
                if number < roll.value:
                    roll.value = number
                    getLogger().info(f"[{channelTag}] Updated roll: {number} for {characterName} due to disadvantage")
            roll.secondRoll = SecondRoll.COMPLETED


def getCurrentRound(message):
    if not message.channel.id in rounds:
        getLogger().error(f"[{getChannelTag(message.channel)}] Channel not currently rolling.")
        return None

    return rounds[message.channel.id]


def updateSecondRoll(message, secondRoll):
    currentRound = getCurrentRound(message)
    if currentRound is None:
        return

    userId = message.author.id
    characterKey = currentRound.context.getCharacter(userId)

    channelTag = getChannelTag(message.channel)

    if characterKey is None:
        getLogger().error(f"[{channelTag}] No character for {userId}.")
        return

    if not characterKey in currentRound.playerRolls:
        getLogger().error(f"[{channelTag}] No roll for {characterKey} yet")
        return

    roll = currentRound.playerRolls[characterKey]

    if roll.secondRoll == SecondRoll.COMPLETED:
        getLogger().error(f"[{channelTag}] Already did second roll for {roll.name}")
        return

    roll.secondRoll = secondRoll


def getChannelTag(channel):
    return f"{channel.guild} #{channel.name}"


with open('auth/token', mode='r') as tokenFile:
    configure()
    client.run(tokenFile.read())
