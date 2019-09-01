import logging
import discord
from discord.ext import commands
from operator import itemgetter
from os import linesep
from .base_cog import BaseCog

log = logging.getLogger(__name__)

class Labels(BaseCog):
    """A cog for setting, updating and showing arbitrary info associated with label keys."""

    def __init__(self, bot):
        BaseCog.__init__(self, bot)
        self.bot = bot
        self.label_table = self.bot.database.table('label_table')
        self.bot.info_text += 'Labels:' + linesep + '  The label feature allows users to store (!set) and retrieve (!show) pieces of information - such as images or generic text - in a database for frequent use.' + linesep + linesep

    @commands.command()
    async def set(self, context, label, value):
        """Store a message/image/emote _value_ that can subsequently be displayed via !show _label_. If the label exists, it will be updated with the new value. Please only use lowercase letters."""

        BaseCog.check_forbidden_characters(self, context)

        if any(c.isupper() for c in label):
            await self.bot.post_error(context, 'Your message contains uppercase letters, ' + context.message.author.name + '. To make labels easier to find and use, only all lowercase labels are allowed. Sorry.')
            return

        if self.label_table.contains(self.bot.query.iid == label):
            self.label_table.update({'url': value}, self.bot.query.iid == label)
            await self.bot.post_message(context.message.channel, '**[INFO]** ' + context.message.author.name + ' has updated the label ' + str(label) + '.')
        else:
            self.label_table.insert({'iid': label, 'url': value})
            await self.bot.post_message(context.message.channel, '**[INFO]** ' + context.message.author.name + ' has set a new label ' + str(label) + '.')


    @commands.command()
    async def show(self, context, label):
        """Display a message/image/emote with the given label _label_. Note: This will not work without previously setting up the label using !set _label_ <value>. Use the command !labels to show all available labels."""

        BaseCog.check_forbidden_characters(self, context)

        if not self.label_table.contains(self.bot.query.iid == label):
            await self.bot.post_error(context, 'The label ' + label + ' does not exist, ' + context.message.author.name + '.')
        else:
            url = self.label_table.get(self.bot.query.iid == label)['url']
            await self.bot.post_message(context.message.channel, url)


    @commands.command()
    async def labels(self, context):
        """Shows a list of images/messages/emotes that can be shown using !show <label> and set/updated using !set <label> <value>."""

        BaseCog.check_forbidden_characters(self, context)

        if self.label_table:
            result = '```Labels: ' + linesep

            sorted_label_table = sorted(self.label_table.all(), key=itemgetter('iid'), reverse=False)

            for image in sorted_label_table:
                new_part = '  ' + image['iid'] + linesep
                new_string = result + new_part

                if len(new_string) > 1997:
                    await self.bot.post_message(context.message.channel, result + '```')
                    result = '```'

                result += new_part

            result += '```'
            await self.bot.post_message(context.message.channel, result)
        else:
            await self.bot.post_message(context.message.channel, '**[INFO]** There are no labels.')


    @commands.command()
    async def delete(self, context, label):
        """Remove a message/image/emote with label _label_ from the database."""

        BaseCog.check_forbidden_characters(self, context)

        if not self.label_table.contains(self.bot.query.iid == label):
            await self.bot.post_error(context, 'The label ' + label + ' does not exist, ' + context.message.author.name + '.')
        else:
            self.label_table.remove(self.bot.query.iid == label)
            await self.bot.post_message(context.message.channel, '**[INFO]** ' + context.message.author.name + ' has deleted the label ' + str(label) + '.')


def setup(bot):
    """Labels cog load."""
    bot.add_cog(Labels(bot))
    log.info("Labels cog loaded")
