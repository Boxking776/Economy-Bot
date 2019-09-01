import logging
from conf import config
from bot import EconomyBot

logging.basicConfig(filename=config.logfile, format='%(asctime)s - [%(levelname)s] %(name)s : %(message)s')
log = logging.getLogger(__name__)

try:
    bot = EconomyBot(command_prefix=config.prefix, description=config.description)
    bot.run(config.token)
except Exception as e:
    log.exception(e)
