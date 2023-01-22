#!/usr/bin/python3

import json

from logging_config import getLogger

CHARACTER_KEY = "character"
USER_ID_KEY = "user_id"
USER_RECORDS_KEY = "user_records"
ADMIN_KEY = "admin"
EVERYONE_KEY = "everyone"


class ChannelContext:
    @staticmethod
    def load(channelId):
        try:
            with open(ChannelContext._getConfigFile(channelId)) as config_file:
                config = json.load(config_file)
                return ChannelContext(channelId, config)
        except FileNotFoundError:
            getLogger().info(f"[{channelId}] Creating config.")
            return ChannelContext(channelId, {})

    def admin(self):
        if not ADMIN_KEY in self.config:
            return None

        return self.config[ADMIN_KEY]

    def setAdmin(self, userId):
        self.config[ADMIN_KEY] = userId
        self._saveConfig()

    def everyoneId(self):
        if not EVERYONE_KEY in self.config:
            return None

        return self.config[EVERYONE_KEY]

    def getUserId(self, character):
        if not USER_RECORDS_KEY in self.config:
            return None

        for userRecord in self.config[USER_RECORDS_KEY]:
            if userRecord[CHARACTER_KEY] == character:
                return userRecord[USER_ID_KEY]

        return None


    def getCharacter(self, userId):
        if not USER_RECORDS_KEY in self.config:
            return None

        for userRecord in self.config[USER_RECORDS_KEY]:
            if userRecord[USER_ID_KEY] == userId:
                return userRecord[CHARACTER_KEY]

        return None

    def setCharacter(self, userId, character):
        if not USER_RECORDS_KEY in self.config:
            self.config[USER_RECORDS_KEY] = []

        for userRecord in self.config[USER_RECORDS_KEY]:
            if userRecord[USER_ID_KEY] == userId:
                userRecord[CHARACTER_KEY] = character
                break
        else:
            self.config[USER_RECORDS_KEY].append({
                USER_ID_KEY: userId,
                CHARACTER_KEY: character})
        self._saveConfig()

    def __init__(self, channelId, config):
        # Look up config for channel by ID (if found)
        self.channelId = channelId
        self.config = config

    def _saveConfig(self):
        with open(ChannelContext._getConfigFile(self.channelId), mode="w") as config_file:
            json.dump(self.config, config_file)

    @staticmethod
    def _getConfigFile(channelId):
        return f".config/channel_{channelId}"
