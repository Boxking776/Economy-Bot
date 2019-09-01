import logging
import socket
from os import linesep
import sys 
import asyncio
from traceback import format_exc
from aiohttp import AsyncResolver, ClientSession, TCPConnector
import aiodns
from dependency_load_error import DependencyLoadError
import discord
from discord.ext import commands
from conf import config
from tinydb import TinyDB, Query

log = logging.getLogger(__name__)

__all__ = ('EconomyBot')

class EconomyBot(commands.Bot):
    """The Economy bot."""

    def __init__(self, **kwargs):
        try:
            super().__init__(**kwargs)

            self.http_session = ClientSession(
                connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)
            )

            # Main database for current season
            self.database = TinyDB(config.database)
            self.query = Query()
            log.info('Main database loaded')

            self.info_text = ''
            self.info_text += linesep + linesep + config.description
            self.info_text += linesep + linesep + 'Admins:'

            for admin in config.admins:
                self.info_text += linesep + '  ' + admin

            self.info_text += linesep + linesep + config.additional_info_text
            self.info_text += linesep + linesep + 'Type !help to see a list of available commands.' + linesep + linesep

            amnt_failed = 0 

            # TimedTask must be started first if at all
            if 'timed_task' in config.cogs and config.cogs[0] != 'timed_task':
                log.fatal('TimedTask is specified to be loaded; has to be loaded first!')
                sys.exit()

            # Go through cogs and load them as extensions
            # NOTE: Each cog adds its own bit to _self.info_text_
            for cog_name in config.cogs:
                try:
                    cog_name = 'Cogs.' + cog_name
                    self.load_extension(cog_name)
                except Exception as e:
                    amnt_failed += 1
                    log.error(f'Failed to load extension {cog_name}: {repr(e)} {format_exc()}')
                else:
                    log.info('Loading extension ' + cog_name)
 
            # If any cogs aren't loaded, bot behaviour is undefined because many cogs depend on each other - better not execute the thing and let the bot admin figure out what's going on.
            if amnt_failed > 0:
                log.fatal('Summary:\n Num failed extension loads: %d', amnt_failed)
                sys.exit()

            self.info_text += 'Some additional information:' + linesep + '  Please be aware of the fact that there may be bugs in the system. There are fail-safe mechanisms, but they may not always prevent a loss of ' + config.currency_name + 's in case of an error.'
        except Exception as e:
            # If any exception occurs at this point, better not execute the thing and let the bot admin figure out what's going on.
            log.exception(e)
            sys.exit()


    async def on_ready(self):
        print('Ready for use.')
        print('--------------')
        self.bot_channel = self.get_channel(config.bot_channel_id)
        print(self.bot_channel)


    async def on_command_error(self, context, error):
        try:
            if isinstance(error, commands.CheckFailure):
                if str(error):
                    await self.post_error(context, str(error))
                else: # wrong channel does not post an error, but still marks message as invalid
                    await context.message.add_reaction('\U0000274C')
            elif isinstance(error, commands.MissingRequiredArgument):
                await self.post_error(context, 'A required argument is missing, ' + context.message.author.name + '.')
            elif isinstance(error, commands.ArgumentParsingError):
                await self.post_error(context, 'An error occurred parsing your supplied arguments, ' + context.message.author.name + '. Please try again.')
            elif isinstance(error, commands.ExpectedClosingQuoteError):
                await self.post_error(context, 'Your input is missing a closing quote, ' + context.message.author.name + '. Please try again.')
            elif isinstance(error, commands.CommandNotFound):
                await self.post_error(context, 'This command does not exist, ' + context.message.author.name + '. Sorry.')
            elif isinstance(error, commands.UserInputError):
                await self.post_error(context, 'A general input error occurred, ' + context.message.author.name + '. Sorry. Please try again.')
            elif isinstance(error, DependencyLoadError):
                await self.post_error(context, 'This feature is currently not available, ' + context.message.author.name + '. Sorry. Please notify your bot admin about loading the required dependencies.')
            else:
                raise error
        except Exception as e:
            await self.post_error(context, 'Oh no, something went wrong. ' + config.additional_error_message)
            log.exception(e)


    async def post_error(self, context, error_text, add_error_message = ''):
        """Has the bot post an error message in the bot channel. Quotes original message for context. Reacts to original message with an X emote to notify the message author."""

        try:
            await context.message.add_reaction('\U0000274C')

            # Note: Error is always posted in the bot channel even for commands that are allowed in other channels. This is to prevent spam abuse.
            # Note: Avoid abuse by stripping forbidden characters, which might break the quote formatting or make the bot tag @everyone.
            message_minus_forbidden = context.message.content.replace('@', '')
            message_minus_forbidden = message_minus_forbidden.replace('`', '')
            quote = '`' + context.message.author.name + ': ' + message_minus_forbidden + '`' + linesep + linesep
            await self.post_message(self.bot_channel, quote + '**[ERROR]** ' + error_text + ' ' + add_error_message)
        except Exception as e:
            log.fatal('EXCEPTION OCCURRED WHILE POSTING ERROR:')
            log.exception(e)


    async def post_message(self, channel, message_text, embed = None):
        """Has the bot post a message in the respective channel."""

        try:
            if embed is None:
                # Discord character limit is 2000; split up the message if it's too long
                chunk_size = 2000

                if message_text.startswith('```') and message_text.endswith('```'):
                    message_text = message_text[3:]
                    message_text = message_text[:-3]
                    chunk_size = 1994

                for i in range(0, len(message_text), chunk_size):
                    text_chunk = message_text[i:i+chunk_size]

                    if chunk_size == 1994:
                        text_chunk = '```' + text_chunk
                        text_chunk += '```'

                    attempts = 0

                    while attempts < config.repost_attempts:
                        try:
                            return await channel.send(text_chunk)
                        except discord.errors.HTTPException:
                            attempts += 1
                            await asyncio.sleep(2)
            else:
                attempts = 0

                while attempts < config.repost_attempts:
                    try:
                        return await channel.send(embed=embed)
                        break
                    except discord.errors.HTTPException:
                        attempts += 1
                        await asyncio.sleep(2)
        except Exception as e:
            await self.bot_channel.send('**[ERROR]** A critical error occurred.' + ' ' + config.additional_error_message)
            log.fatal('EXCEPTION OCCURRED WHILE POSTING MESSAGE:')
            log.exception(e)
