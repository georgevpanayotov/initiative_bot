import logging


def configure():
    logger = logging.getLogger("discord.initiative")

    handler = logging.FileHandler("log.txt")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)


def getLogger():
    return logging.getLogger("discord.initiative")
