#!/usr/bin/python3

import discord
import os
import re

from channel_context import ChannelContext
from discord import Intents
from logging_config import configure
from logging_config import getLogger
from parsing import parseEither
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

            if currentRound.context.admin() is None:
                getLogger().error(f"[{channelTag}] Roll ignored before admin chosen.")
                return

            allNumbers = []
            number = None
            for field in embed.fields:
                newNumber = parseNumbers(field.name)
                if newNumber is not None:
                    number = newNumber

                allNumbers.append(parseEither(field.name))

            roll = Roll(embed.author.name, number, allNumbers)

            handleRoll(channelTag, currentRound, roll)

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

                # Reset so that admin has to request rolling again.
                del rounds[message.channel.id]
            else:
                await message.channel.send(f"I didn't ask you!")
        elif message.content.startswith("/initiative I am"):
            currentRound = getCurrentRound(message, True)
            if currentRound is None:
                context = ChannelContext.load(channelTag, message.channel.id)
            else:
                context = currentRound.context

            parts = message.content.split(" ")
            characterKey = parts[3].strip().lower()

            userId = message.author.id

            getLogger().info(f"[{channelTag}] {characterKey} is {message.author.name} ({userId})")
            context.setCharacter(userId, characterKey)
        elif message.content.startswith("/initiative advantage"):
            updateSecondRoll(message, SecondRoll.ADVANTAGE)
        elif message.content.startswith("/initiative disadvantage"):
            updateSecondRoll(message, SecondRoll.DISADVANTAGE)
        elif message.content.startswith("/initiative normal"):
            normalizeRoll(message)
        elif message.content == "/initiative get":
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            if message.author.id != currentRound.context.admin():
                getLogger().error("[{channelTag}] Non admin tried to get summary.")
                await message.channel.send("Only admin can do that.")
                return

            allRolls = []
            allRolls.extend(currentRound.playerRolls.values())
            allRolls.extend(currentRound.npcRolls)

            response = ""
            for i, roll in enumerate(sorted(allRolls,
                                            key = lambda roll: roll.value,
                                            reverse = True)):
                response = response + roll.name + " got " + str(roll.value)
                if i != len(allRolls) - 1:
                    response = response + "\n"

            del rounds[message.channel.id]

            if len(response) == 0:
                return
            getLogger().info(f"[{channelTag}] Summary done.")
            await message.channel.send(response)


def handleRoll(channelTag, currentRound, roll):
    characterKey = roll.name.split(" ")[0].strip().lower()

    userId = currentRound.context.getUserId(characterKey)

    if userId is not None:
        handlePlayerRoll(channelTag, currentRound, roll)
    else:
        handleNpcRoll(channelTag, currentRound, roll)


def handleNpcRoll(channelTag, currentRound, roll):
    getLogger().info(f"[{channelTag}] Roll: {roll.value} for NPC {roll.name}")
    currentRound.npcRolls.append(roll)


def handlePlayerRoll(channelTag, currentRound, newRoll):
    characterKey = newRoll.name.split(" ")[0].strip().lower()

    if not characterKey in currentRound.playerRolls:
        currentRound.playerRolls[characterKey] = newRoll
        getLogger().info(f"[{channelTag}] Roll: {newRoll.value} for {newRoll.name}")
    else:
        roll = currentRound.playerRolls[characterKey]
        if roll.secondRoll is None:
            getLogger().error(f"[{channelTag}] Rejected Roll: {newRoll.value} for {newRoll.name}")
        elif roll.secondRoll == SecondRoll.COMPLETED:
            getLogger().error(f"[{channelTag}] Rejected Second Roll: {newRoll.value} for {newRoll.name}")
        else:
            if roll.secondRoll == SecondRoll.ADVANTAGE:
                if newRoll.value > roll.value:
                    roll.value = newRoll.value
                    getLogger().info(f"[{channelTag}] Updated roll: {newRoll.value} for {newRoll.name} due to advantage")
            elif roll.secondRoll == SecondRoll.DISADVANTAGE:
                if newRoll.value < roll.value:
                    roll.value = newRoll.value
                    getLogger().info(f"[{channelTag}] Updated roll: {newRoll.value} for {newRoll.name} due to disadvantage")

            roll.allNumbers.append(newRoll.value)
            roll.secondRoll = SecondRoll.COMPLETED


def getCurrentRound(message, quiet = False):
    if not message.channel.id in rounds:
        if not quiet:
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

    if len(roll.allNumbers) == 1:

        # This allows for a second roll in order to handle (dis)advantage.
        roll.secondRoll = secondRoll
    elif len(roll.allNumbers) == 2:
        if secondRoll == SecondRoll.ADVANTAGE:
            roll.value = max(roll.allNumbers)
        elif secondRoll == SecondRoll.DISADVANTAGE:
            roll.value = min(roll.allNumbers)
        getLogger().info(f"[{channelTag}] updating {roll.value} for {roll.name} due to {secondRoll}")


def normalizeRoll(message):
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
    getLogger().info(f"[{channelTag}] Normalizing {roll.value} for {roll.name}.")

    # Pick the first roll so it's like we didn't do advantage at all.
    roll.value = roll.allNumbers[0]


def getChannelTag(channel):
    return f"{channel.guild} #{channel.name}"


with open('auth/token', mode='r') as tokenFile:
    configure()
    client.run(tokenFile.read())
