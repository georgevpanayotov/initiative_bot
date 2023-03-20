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
    def load(channelTag, channelId):
        filename = ChannelContext._getConfigFile(channelId)
        try:
            with open(filename) as config_file:
                config = json.load(config_file)

                ChannelContext._validateConfig(channelTag, config)

                return ChannelContext(channelId, config)
        except FileNotFoundError:
            getLogger().info(f"[{channelTag}] Creating config.")
            return ChannelContext(channelId, {})
        except json.decoder.JSONDecodeError as e:
            getLogger().error(f"[{channelTag}] {filename}:{e.lineno}:{e.colno}: Malformed config: {e.msg}.")
            raise ConfigException(f"Error: Malformed config!") from e

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
            json.dump(self.config, config_file, indent=4)

    @staticmethod
    def _getConfigFile(channelId):
        return f".config/channel_{channelId}"


    @staticmethod
    def _validateConfig(channelTag, config):
        keySet = set(config.keys()) - {EVERYONE_KEY, USER_RECORDS_KEY, ADMIN_KEY}
        if len(keySet) > 0:
            getLogger().error(f"[{channelTag}] Unexpected top level keys: {keySet}.")
            raise ConfigException("Error: Invalid top level config.")

        if EVERYONE_KEY in config:
            if not isinstance(config[EVERYONE_KEY], int):
                getLogger().error(f"[{channelTag}] Everyone user id must be an int.")
                raise ConfigException("Error: Invalid `everyone` config.")

        if ADMIN_KEY in config:
            if not isinstance(config[ADMIN_KEY], int):
                getLogger().error(f"[{channelTag}] Admin user id must be an int.")
                raise ConfigException("Error: Invalid `admin` config.")

        if USER_RECORDS_KEY in config:
            records = config[USER_RECORDS_KEY]
            if not isinstance(records, list):
                getLogger().error(f"[{channelTag}] User records must be a list.")
                raise ConfigException("Error: Invalid `user records` config.")

            for i, record in enumerate(records):
                if not isinstance(record, dict):
                    getLogger().error(f"[{channelTag}] User record {i + 1} must be a dict.")
                    raise ConfigException("Error: Invalid `user record` config.")

                if not set(record.keys()) == {USER_ID_KEY, CHARACTER_KEY}:
                    getLogger().error(f"[{channelTag}] Invalid keys in user record {i + 1}: {record.keys()}.")
                    raise ConfigException("Error: Invalid `user record` keys in config.")

                if not isinstance(record[CHARACTER_KEY], str):
                    getLogger().error(f"[{channelTag}] Character name for user record {i + 1} must be string.")
                    raise ConfigException("Error: Invalid character name in config.")

                if not isinstance(record[USER_ID_KEY], int):
                    getLogger().error(f"[{channelTag}] User id for user record {i + 1} must be int.")
                    raise ConfigException("Error: Invalid user id in config.")


class ConfigException(Exception):
    pass
