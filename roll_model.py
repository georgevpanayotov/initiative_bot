#!/usr/bin/python3

from channel_context import ChannelContext
from enum import Enum

class SecondRoll(Enum):
    ADVANTAGE = 1
    DISADVANTAGE = 2
    COMPLETED = 3

class Roll:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        # For now, we are just expecting a first roll. This will change if we have to update for
        # advantage.
        self.secondRoll = None


# Represents a round of rolling for initiative.
class RollingRound:
    def __init__(self, channelTag, channelId):
        self.context = ChannelContext.load(channelTag, channelId)
        self.playerRolls = {}
        self.maybeAdmin = None
