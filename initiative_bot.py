#!/usr/bin/python3

import discord
import os
import re

from channel_context import ChannelContext
from channel_context import ConfigException
from discord import Embed
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

        matchInitiative = re.compile("Initiative\s*\([+-]?(\d*)\)")

        if embed.title is not None and matchInitiative.match(embed.title) is not None:
            await handleRoll(message)

    else:
        if message.content == "/initiative" or message.content == "/init":
            # Initialize a rolling round.
            try:
                currentRound = RollingRound(channelTag, message.channel.id)
            except ConfigException as e:
                await message.channel.send(str(e))
                return

            rounds[message.channel.id] = currentRound

            if currentRound.context.admin() is None:
                currentRound.maybeAdmin = message.author.id
                getLogger().info(f"{channelTag} Trying to find admin.")
                await message.channel.send(f"No admin found. Are you the admin, <@{message.author.id}>?")
            elif message.author.id == currentRound.context.admin():
                getLogger().info(f"{channelTag} Starting round.")
                everyone = currentRound.context.everyoneId()
                await message.channel.send(f"<@&{everyone}>, roll for initiative.")
            else:
                getLogger().error(f"{channelTag} Non-admin tried to start a round.")
                del rounds[message.channel.id]
                await message.channel.send(f"Only admin can do that.")
        elif message.content == "/initiative yes" or message.content == "/init yes":
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            if currentRound.maybeAdmin is not None and currentRound.maybeAdmin == message.author.id:
                currentRound.maybeAdmin = None
                currentRound.context.setAdmin(message.author.id)
                getLogger().info(f"{channelTag} Found admin.")

                # Reset so that admin has to request rolling again.
                del rounds[message.channel.id]
            else:
                await message.channel.send(f"I didn't ask you!")
        elif (message.content.startswith("/initiative I am") or
              message.content.startswith("/init I am")):
            currentRound = getCurrentRound(message, True)
            if currentRound is None:
                try:
                    context = ChannelContext.load(channelTag, message.channel.id)
                except ConfigException as e:
                    await message.channel.send(str(e))
                    return
            else:
                context = currentRound.context

            parts = message.content.split(" ")
            characterKey = parts[3].strip().lower()

            userId = message.author.id

            getLogger().info(f"{channelTag} {characterKey} is {message.author.name} ({userId})")
            context.setCharacter(userId, characterKey)
        elif (message.content.startswith("/initiative advantage") or
              message.content.startswith("/init advantage")):
            success = updateSecondRoll(message, SecondRoll.ADVANTAGE)
            if not success:
                await message.channel.send(f"<@{message.author.id}> hasn't rolled yet.")
        elif (message.content.startswith("/initiative disadvantage") or
              message.content.startswith("/init disadvantage")):
            success = updateSecondRoll(message, SecondRoll.DISADVANTAGE)
            if not success:
                await message.channel.send(f"<@{message.author.id}> hasn't rolled yet.")
        elif (message.content.startswith("/initiative normal") or
              message.content.startswith("/init normal")):
            success = normalizeRoll(message)
            if not success:
                await message.channel.send(f"<@{message.author.id}> hasn't rolled yet.")
        elif message.content == "/initiative get" or message.content == "/init get":
            currentRound = getCurrentRound(message)
            if currentRound is None:
                return

            if message.author.id != currentRound.context.admin():
                getLogger().error("{channelTag} Non admin tried to get summary.")
                await message.channel.send("Only admin can do that.")
                return

            await computeInitiative(currentRound, message.channel)


async def handleRoll(message):
    embed = message.embeds[0]
    channelTag = getChannelTag(message.channel)
    currentRound = getCurrentRound(message)
    if currentRound is None:
        return

    if currentRound.context.admin() is None:
        getLogger().error(f"{channelTag} Roll ignored before admin chosen.")
        return

    allNumbers = []
    number = None
    for field in embed.fields:
        newNumber = parseNumbers(field.name)
        if newNumber is not None:
            number = newNumber

        allNumbers.append(parseEither(field.name))

    roll = Roll(embed.author.name, number, allNumbers)

    success = False
    userId = currentRound.context.getUserId(roll.key)

    if userId is not None:
        success = handlePlayerRoll(channelTag, currentRound, roll)
    else:
        success = handleNpcRoll(channelTag, currentRound, roll)

    if not success:
        userId = currentRound.context.getUserId(roll.key)

        nameToMention = embed.author.name
        if userId is not None:
            nameToMention = f"<@{userId}>"

        await message.channel.send(f"{nameToMention} has already rolled.")



def handleNpcRoll(channelTag, currentRound, roll):
    getLogger().info(f"{channelTag} Roll: {roll.value} for NPC {roll.name}")
    currentRound.npcRolls.append(roll)

    return True


def handlePlayerRoll(channelTag, currentRound, newRoll):
    characterKey = newRoll.key

    if not characterKey in currentRound.playerRolls:
        currentRound.playerRolls[characterKey] = newRoll
        getLogger().info(f"{channelTag} Roll: {newRoll.value} for {newRoll.name}")
    else:
        roll = currentRound.playerRolls[characterKey]
        if roll.secondRoll is None:
            getLogger().error(f"{channelTag} Rejected Roll: {newRoll.value} for {newRoll.name}")
            return False
        elif roll.secondRoll == SecondRoll.COMPLETED:
            getLogger().error(f"{channelTag} Rejected Second Roll: {newRoll.value} for {newRoll.name}")
            return False
        else:
            if roll.secondRoll == SecondRoll.ADVANTAGE:
                if newRoll.value > roll.value:
                    roll.value = newRoll.value
                    getLogger().info(f"{channelTag} Updated roll: {newRoll.value} for {newRoll.name} due to advantage")
            elif roll.secondRoll == SecondRoll.DISADVANTAGE:
                if newRoll.value < roll.value:
                    roll.value = newRoll.value
                    getLogger().info(f"{channelTag} Updated roll: {newRoll.value} for {newRoll.name} due to disadvantage")

            roll.allNumbers.append(newRoll.value)
            roll.secondRoll = SecondRoll.COMPLETED

    return True

def getCurrentRound(message, quiet = False):
    if not message.channel.id in rounds:
        if not quiet:
            getLogger().error(f"{getChannelTag(message.channel)} Channel not currently rolling.")
        return None

    return rounds[message.channel.id]


def updateSecondRoll(message, secondRoll):
    currentRound = getCurrentRound(message)
    if currentRound is None:
        return False

    userId = message.author.id
    characterKey = currentRound.context.getCharacter(userId)

    channelTag = getChannelTag(message.channel)

    if characterKey is None:
        getLogger().error(f"{channelTag} No character for {userId}.")
        return False

    if not characterKey in currentRound.playerRolls:
        getLogger().error(f"{channelTag} No roll for {characterKey} yet")
        return False

    roll = currentRound.playerRolls[characterKey]

    if len(roll.allNumbers) == 1:

        # This allows for a second roll in order to handle (dis)advantage.
        roll.secondRoll = secondRoll
    elif len(roll.allNumbers) == 2:
        if secondRoll == SecondRoll.ADVANTAGE:
            roll.value = max(roll.allNumbers)
        elif secondRoll == SecondRoll.DISADVANTAGE:
            roll.value = min(roll.allNumbers)
        getLogger().info(f"{channelTag} updating {roll.value} for {roll.name} due to {secondRoll}")

    return True


def normalizeRoll(message):
    currentRound = getCurrentRound(message)
    if currentRound is None:
        return False

    userId = message.author.id
    characterKey = currentRound.context.getCharacter(userId)

    channelTag = getChannelTag(message.channel)

    if characterKey is None:
        getLogger().error(f"{channelTag} No character for {userId}.")
        return False

    if not characterKey in currentRound.playerRolls:
        getLogger().error(f"{channelTag} No roll for {characterKey} yet")
        return False

    roll = currentRound.playerRolls[characterKey]
    getLogger().info(f"{channelTag} Normalizing {roll.value} for {roll.name}.")

    # Pick the first roll so it's like we didn't do advantage at all.
    roll.value = roll.allNumbers[0]

    return True


async def computeInitiative(currentRound, channel):
    allRolls = []
    allRolls.extend(currentRound.playerRolls.values())
    allRolls.extend(currentRound.npcRolls)

    pigeonImage = discord.File("images/george_method.png", filename="george_method.png")

    logSummary = ""
    response = Embed(title = "Initiative results.")
    response.set_footer(text = "Initiative bot. A PigeonWorks project.",
                        icon_url = "attachment://george_method.png")
    response.colour = discord.Colour.orange()
    for i, roll in enumerate(sorted(allRolls,
                                    key = lambda roll: roll.value,
                                    reverse = True)):
        response.add_field(name = roll.name, value = str(roll.value), inline = False)
        logSummary = logSummary + f"{roll.name}({roll.value})"
        if i < len(allRolls) - 1:
            logSummary = logSummary + ", "

    del rounds[channel.id]

    channelTag = getChannelTag(channel)

    if len(response.fields) == 0:
        getLogger().warning(f"{channelTag} Summary: no rolls.")
        response.add_field(name = "Nobody rolled", value = "", inline = False)
        await channel.send(embed = response, file = pigeonImage)

        return

    getLogger().info(f"{channelTag} Summary done: {logSummary}.")
    await channel.send(embed = response, file = pigeonImage)


def getChannelTag(channel):
    return f"[{channel.guild} #{channel.name}]"


with open('auth/token', mode='r') as tokenFile:
    configure()
    client.run(tokenFile.read())
