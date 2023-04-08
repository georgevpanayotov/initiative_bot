import logging


def configure():
    rootLogger = logging.getLogger("discord")
    rootHandler = logging.FileHandler("rootlog.txt")
    rootHandler.setLevel(logging.INFO)
    rootHandler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    rootLogger.addHandler(rootHandler)

    errorHandler = logging.FileHandler("errorlog.txt")
    errorHandler.setLevel(logging.ERROR)
    errorHandler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    rootLogger.addHandler(errorHandler)

    logger = logging.getLogger("discord.initiative")

    handler = logging.FileHandler("log.txt")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)


def getLogger():
    return logging.getLogger("discord.initiative")
