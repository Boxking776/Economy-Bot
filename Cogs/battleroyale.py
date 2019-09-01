import logging
import json
import discord
from discord.ext import commands
from tinydb.operations import increment
from tinydb.operations import subtract
from collections import defaultdict
from operator import itemgetter
import math
import datetime
import asyncio
import random
from os import linesep
from .base_cog import BaseCog
from conf import config
from dependency_load_error import DependencyLoadError

log = logging.getLogger(__name__)

class BattleRoyale(BaseCog):
    """A cog for the battle royale minigame."""

    def __init__(self, bot):
        BaseCog.__init__(self, bot)
        self.br_participants = []
        self.br_holiday_points_used = []
        self.br_last_ann = ''
        self.br_pool = 0
        self.br_bet = 0
        self.br_closed = True

        with open(config.cogs_data_path + '/gambling.json', 'r') as gambling_config:
            data = json.load(gambling_config)
            self.arena_init_texts = data['arena_init_texts']
            self.custom_weapons = data['custom_weapons']
            self.custom_suicides = data['custom_suicides']
            self.suicide_emotes = data['suicide_emotes']
            self.exotic_weapons = data['exotic_weapons']

        self.br_delay = int(config.get('BattleRoyale', 'br_delay', fallback=180))
        self.br_min_bet = int(config.get('BattleRoyale', 'br_min_bet', fallback=5))
        self.br_min_users = int(config.get('BattleRoyale', 'br_min_users', fallback=3))
        self.p_suicide = float(config.get('BattleRoyale', 'p_suicide', fallback=1))
        self.p_block = float(config.get('BattleRoyale', 'p_block', fallback=0.3))
        self.p_bomb_or_melee = float(config.get('BattleRoyale', 'p_bomb_or_melee', fallback=0.15))
        self.p_exotic = float(config.get('BattleRoyale', 'p_exotic', fallback=0.05))

        if (self.br_min_users < 3):
            raise RuntimeError('Minimum number of BR participants is 3!')

        # Register battle royale to be a possible minigame for holiday points
        holidays = self.bot.get_cog('Holidays')

        if holidays is not None:
            holidays.minigames.append('Battle Royale')


    #================ BASECOG INTERFACE ================
    def extend_check_options(self, db_entry):
        result_string = 'Battle royales fought'.ljust(config.check_ljust) + ' ' + str(db_entry['brs']) + linesep \
                      + 'Battle royale wins'.ljust(config.check_ljust) + ' ' + str(db_entry['br_wins']) + linesep \
                      + 'Total battle royale score'.ljust(config.check_ljust) + ' ' + str(db_entry['br_score']) + linesep \
                      + 'Total battle royale winnings'.ljust(config.check_ljust) + ' ' + str(db_entry['br_winnings'])

        return result_string


    def extend_trivia_table(self, trivia_table):
        trivia_table.insert({'name': 'highest_br_pool', 'value': 0, 'person1': '', 'person2': '', 'date': ''})
        trivia_table.insert({'name': 'largest_br', 'value': 0, 'person1': '', 'person2': '', 'date': ''})
        trivia_table.insert({'name': 'amnt_brs', 'value': 0, 'person1': '', 'person2': '', 'date': ''})
        trivia_table.insert({'name': 'most_br_score', 'value': 0, 'person1': '', 'person2': '', 'date': ''})
        trivia_table.insert({'name': 'longest_streak', 'value': 0, 'person1': '', 'person2': '', 'date': ''})


    def extend_trivia_output(self, trivia_table):
        result = ''

        try:
            amnt_brs = trivia_table.get(self.bot.query.name == 'amnt_brs')

            if amnt_brs['value'] > 0:
                result += 'Total amount of battle royales fought'.ljust(config.trivia_ljust) + '  ' + str(amnt_brs['value']) + linesep
        except Exception:
            pass

        try:
            highest_br_pool = trivia_table.get(self.bot.query.name == 'highest_br_pool')

            if highest_br_pool['person1'] != '':
                result += 'Highest battle royale prize pool'.ljust(config.trivia_ljust) + '  ' + str(highest_br_pool['value']) + ' won by ' + highest_br_pool['person1'] + ' with score ' + str(highest_br_pool['person2']) + ' on ' + highest_br_pool['date'] + linesep
        except Exception:
            pass

        try:
            largest_br = trivia_table.get(self.bot.query.name == 'largest_br')

            if largest_br['person1'] != '':
                result += 'Most participants in a battle royale'.ljust(config.trivia_ljust) + '  ' + str(largest_br['value']) + ' won by ' + largest_br['person1'] + ' with score ' + str(largest_br['person2']) + ' on ' + largest_br['date'] + linesep
        except Exception:
            pass

        try:
            most_kills = trivia_table.get(self.bot.query.name == 'most_br_score')

            if most_kills['person1'] != '':
                result += 'Highest score in a battle royale'.ljust(config.trivia_ljust) + '  ' + str(most_kills['value']) + ' by ' + most_kills['person1'] + ' (won by ' + most_kills['person2'] + ') on ' + most_kills['date'] + linesep
        except Exception:
            pass

        try:
            longest_streak = trivia_table.get(self.bot.query.name == 'longest_streak')

            if longest_streak['person1'] != '':
                result += 'Longest kill streak in a battle royale'.ljust(config.trivia_ljust) + '  ' + str(longest_streak['value']) + ' by ' + longest_streak['person1'] + ' (won by ' + longest_streak['person2'] + ') on ' + longest_streak['date'] + linesep + linesep
        except Exception:
            pass

        return result


    def extend_season_output(self, number, season_trivia_table, season_main_db, season_tables):
        result = ''

        try:
            amnt_brs = season_trivia_table.get(self.bot.query.name == 'amnt_brs')

            if amnt_brs['value'] > 0:
                result += 'Total amount of battle royales fought'.ljust(config.season_ljust) + '  ' + str(amnt_brs['value']) + linesep
        except Exception:
            pass

        try:
            highest_br_pool = season_trivia_table.get(self.bot.query.name == 'highest_br_pool')

            if highest_br_pool['person1'] != '':
                result += 'Highest battle royale prize pool'.ljust(config.season_ljust) + '  ' + str(highest_br_pool['value']) + ' won by ' + highest_br_pool['person1'] + ' with score ' + str(highest_br_pool['person2']) + ' on ' + highest_br_pool['date'] + linesep
        except Exception:
            pass

        try:
            largest_br = season_trivia_table.get(self.bot.query.name == 'largest_br')

            if largest_br['person1'] != '':
                result += 'Most participants in a battle royale'.ljust(config.season_ljust) + '  ' + str(largest_br['value']) + ' won by ' + largest_br['person1'] + ' with score ' + str(largest_br['person2']) + ' on ' + largest_br['date'] + linesep + linesep
        except Exception:
            pass

        try:
            most_kills = season_trivia_table.get(self.bot.query.name == 'most_br_score')

            if most_kills['person1'] != '':
                result += 'Highest score in a battle royale'.ljust(config.season_ljust) + '  ' + str(most_kills['value']) + ' by ' + most_kills['person1'] + ' (won by ' + most_kills['person2'] + ') on ' + most_kills['date'] + linesep
        except Exception:
            pass

        try:
            most_brs = max(season_main_db.all(), key=itemgetter('brs'))

            if most_brs['brs'] > 0:
                result += 'Most battle royales fought'.ljust(config.season_ljust) + '  ' + str(most_brs['brs']) + ' by ' + most_brs['user'] + linesep
        except Exception:
            pass

        try:
            most_br_wins = max(season_main_db.all(), key=itemgetter('br_wins'))

            if most_br_wins['br_wins'] > 0:
                result += 'Most battle royale wins'.ljust(config.season_ljust) + '  ' + str(most_br_wins['br_wins']) + ' by ' + most_br_wins['user'] + linesep
        except Exception:
            pass

        try:
            most_br_score = max(season_main_db.all(), key=itemgetter('br_score'))

            if most_br_score['br_score'] > 0:
                result += 'Highest total battle royale score'.ljust(config.season_ljust) + '  ' + str(most_br_score['br_score']) + ' by ' + most_br_score['user'] + linesep
        except Exception:
            pass

        try:
            highest_br_winnings = max(season_main_db.all(), key=itemgetter('br_winnings'))

            if highest_br_winnings['br_winnings'] > 0:
                result += ('Most ' + config.currency_name + ' winnings in battle royale').ljust(config.season_ljust) + '  ' + str(highest_br_winnings['br_winnings']) + ' by ' + highest_br_winnings['user'] + linesep
        except Exception:
            pass

        try:
            longest_streak = season_trivia_table.get(self.bot.query.name == 'longest_streak')

            if longest_streak['person1'] != '':
                result += 'Longest kill streak in a battle royale'.ljust(config.season_ljust) + '  ' + str(longest_streak['value']) + ' by ' + longest_streak['person1'] + ' (won by ' + longest_streak['person2'] + ') on ' + longest_streak['date'] + linesep + linesep
        except Exception:
            pass

        return result


    def get_check_message_for_aspect(self, aspect):
        mes = None

        if aspect == 'brs':
            mes = 'Battle royales fought'
        elif aspect == 'br_wins':
            mes = 'Battle royale wins'
        elif aspect == 'br_score':
            mes = 'Total battle royale score'
        elif aspect == 'br_winnings':
            mes = 'Total battle royale winnings'

        return mes


    def get_label_for_command(self, command):
        result = None

        if command == 'br_wins':
            result = 'battle royale wins'
        elif command == 'br_score':
            result = 'battle royale score'
        elif command == 'br_winnings':
            result = 'total battle royale winnings'
        elif command == 'brs':
            result = 'battle royales fought in'

        return result
    #==============================================


    @commands.command()
    async def joinbr(self, context):
        """Joins the battle royale with an entry fee."""

        BaseCog.check_main_server(self, context)
        BaseCog.check_bot_channel(self, context)
        BaseCog.check_forbidden_characters(self, context)
        await BaseCog.dynamic_user_add(self, context)

        economy = BaseCog.load_dependency(self, 'Economy')
        main_db = economy.main_db
        stats = BaseCog.load_dependency(self, 'Stats')
        trivia_table = stats.trivia_table
        gambling = BaseCog.load_dependency(self, 'Gambling')
        weapon_emotes = gambling.weapon_emotes

        is_participating = context.message.author.name in self.br_participants

        try:
            pukcab_pool = self.br_pool

            if self.br_closed:
                await self.bot.post_error(context, 'You are too late to join the recent battle royale, ' + context.message.author.name + '. Start a new one with !battleroyale <bet> if you are so eager to fight.')
            elif context.message.author.name in self.br_participants:
                await self.bot.post_error(context, 'You are already taking part in this battle royale, ' + context.message.author.name + '.')
            else:
                user_balance = main_db.get(self.bot.query.user == context.message.author.name)['balance']

                # Check if battle royale is today's minigame for holiday points
                holidays = self.bot.get_cog('Holidays')
                is_holiday_minigame = False
                holiday = 0

                if holidays is not None:
                    if holidays.holiday_minigame.contains(self.bot.query.minigame == 'Battle Royale'):
                        is_holiday_minigame = True
                        holiday = main_db.get(self.bot.query.user == context.message.author.name)['holiday']

                if user_balance + holiday >= self.br_bet:
                    self.br_participants.append(context.message.author.name)
                    self.br_pool += self.br_bet

                    # Remove entry fee
                    if holiday > 0:
                        leftover = self.br_bet - holiday

                        if leftover > 0: # i.e. br bet > holiday points
                            main_db.update(subtract('holiday', holiday), self.bot.query.user == context.message.author.name)
                            self.br_holiday_points_used.append(holiday)
                            main_db.update(subtract('balance', leftover), self.bot.query.user == context.message.author.name)
                            main_db.update(subtract('gambling_profit', leftover), self.bot.query.user == context.message.author.name)
                        else: # Note: holiday points do not count as negative gambling profit
                            main_db.update(subtract('holiday', self.br_bet), self.bot.query.user == context.message.author.name)
                            self.br_holiday_points_used.append(self.br_bet)
                    else:
                        main_db.update(subtract('balance', self.br_bet), self.bot.query.user == context.message.author.name)
                        main_db.update(subtract('gambling_profit', self.br_bet), self.bot.query.user == context.message.author.name)
                        self.br_holiday_points_used.append(0)

                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** ' + context.message.author.name + ' has joined the challengers! The prize pool is now at ' + str(self.br_pool) + ' ' + config.currency_name + 's.')
                else:
                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** You do not have enough ' + config.currency_name + 's, ' + context.message.author.name + '. The entry fee is ' + str(self.br_bet) + ' ' + config.currency_name + 's and your current balance is ' + str(user_balance) + '.') 
        except Exception as e:
            try:
                if (context.message.author.name in self.br_participants) and not is_participating:
                    self.br_participants.pop()

                    # Careful: We might have crashed before even adding the used holiday points, so can't always pop!
                    if len(self.br_participants) < len(self.br_holiday_points_used):
                        self.br_holiday_points_used.pop()

                self.br_pool = pukcab_pool
                await self.bot.post_error(context, 'Oh no, something went wrong (you are not part of the challengers).', config.additional_error_message)
                log.exception(e)
            except Exception as e2:
                await self.bot.post_error(context, 'Oh no, something went wrong (you are not part of the challengers).', config.additional_error_message)
                log.exception(e2)


    @commands.command()
    async def battleroyale(self, context, bet=None):
        """Starts a battle royale with a forced bet of _bet_ points."""

        BaseCog.check_main_server(self, context)
        BaseCog.check_bot_channel(self, context)
        BaseCog.check_forbidden_characters(self, context)
        await BaseCog.dynamic_user_add(self, context)

        economy = BaseCog.load_dependency(self, 'Economy')
        main_db = economy.main_db
        stats = BaseCog.load_dependency(self, 'Stats')
        trivia_table = stats.trivia_table
        gambling = BaseCog.load_dependency(self, 'Gambling')
        weapon_emotes = gambling.weapon_emotes

        race_participants = None

        try:
            horserace = BaseCog.load_dependency(self, 'Horserace')
            race_participants = horserace.race_participants
        except DependencyLoadError:
            # If horse race cog is not available, shouldn't exit with error
            pass

        try:
            if not bet:
                await self.bot.post_error(context, '!battleroyale requires a forced bet.')
                return

            try:
                bet = int(bet)
            except ValueError:
                await self.bot.post_error(context, 'Bet must be an integer.')
                return

            if self.br_bet != 0:
                await self.bot.post_error(context, 'Not so hasty, courageous fighter. There is already a battle royale in progress.')
                return
            elif race_participants is not None and len(race_participants) > 0:
                await self.bot.post_error(context, 'Sorry ' + context.message.author.name + ', please wait for the ongoing horse race to end so that the messages don\'t interfere.')
            elif bet < self.br_min_bet:
                await self.bot.post_error(context, '!battleroyale requires the initial forced bet to be at least ' + str(self.br_min_bet) + ' ' + config.currency_name + 's.')
                return
            else:
                user_balance = main_db.get(self.bot.query.user == context.message.author.name)['balance']

                # Check if battle royale is today's minigame for holiday points
                holidays = self.bot.get_cog('Holidays')
                is_holiday_minigame = False
                holiday = 0

                if holidays is not None:
                    if holidays.holiday_minigame.contains(self.bot.query.minigame == 'Battle Royale'):
                        is_holiday_minigame = True
                        holiday = main_db.get(self.bot.query.user == context.message.author.name)['holiday']

                if user_balance + holiday < bet:
                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** You do not have enough ' + config.currency_name + 's, ' + context.message.author.name + '. The desired entry fee is ' + str(bet) + ' ' + config.currency_name + 's and your current balance is ' + str(user_balance) + '.') 
                    return

                lock = True
                gambling = self.bot.get_cog('Gambling')

                if gambling is not None:
                    lock = gambling.lock

                if lock:
                    if bet > gambling.lock_max_bet:
                        await self.bot.post_error(context, 'High-stakes gambling is not allowed. Please stay below ' + str(gambling.lock_max_bet) + ' ' + config.currency_name + 's, ' + context.message.author.name + '. Admins can remove this limit using !unlock.') 
                        return

                self.br_participants.append(context.message.author.name)
                self.br_pool = bet
                self.br_bet = bet

                if holiday > 0:
                    leftover = bet - holiday

                    if leftover > 0: # i.e. br bet > holiday points
                        main_db.update(subtract('holiday', holiday), self.bot.query.user == context.message.author.name)
                        self.br_holiday_points_used.append(holiday)
                        main_db.update(subtract('balance', leftover), self.bot.query.user == context.message.author.name)
                        main_db.update(subtract('gambling_profit', leftover), self.bot.query.user == context.message.author.name)
                    else: # Note: holiday points do not count as negative gambling profit
                        main_db.update(subtract('holiday', bet), self.bot.query.user == context.message.author.name)
                        self.br_holiday_points_used.append(bet)
                else:
                    main_db.update(subtract('balance', bet), self.bot.query.user == context.message.author.name)
                    main_db.update(subtract('gambling_profit', bet), self.bot.query.user == context.message.author.name)
                    self.br_holiday_points_used.append(0)

                announcement = self.br_last_ann

                while announcement == self.br_last_ann:
                    announcement = random.choice(self.arena_init_texts).replace('[USER]', context.message.author.name)

                await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** ' + announcement)
                await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** Type !joinbr (entry fee is ' + str(bet) + ') to join the ranks of the challengers.')
                self.br_last_ann = announcement
                self.br_closed = False
                amount_asked = 0

                while len(self.br_participants) < self.br_min_users and amount_asked < 3:
                    if self.br_delay <= 60:
                        await asyncio.sleep(self.br_delay) # during this time, people can use commands to join
                    else:
                        await asyncio.sleep(self.br_delay-60) # during this time, people can use commands to join
                        await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** Battle royale will start in 1 minute. Type !joinbr to take part!')
                        await asyncio.sleep(30) # during this time, people can use commands to join
                        await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** Battle royale will start in 30 seconds. Type !joinbr to take part!')
                        await asyncio.sleep(30) # during this time, people can use commands to join

                    if len(self.br_participants) < self.br_min_users:
                        await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** Waiting for more people to join the bloodshed (min ' + str(self.br_min_users) + ' participants).')

                    amount_asked += 1

                self.br_closed = True

                if len(self.br_participants) < self.br_min_users:
                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** The battle royale has been canceled due to a lack of interest in the bloodshed. Cowards! (min ' + str(self.br_min_users) + ' participants).')
                    for i, p in enumerate(self.br_participants):
                        try:
                            balance_p = main_db.get(self.bot.query.user == p)['balance']
                            gambling_pr = main_db.get(self.bot.query.user == p)['gambling_profit']
                            main_db.update({'gambling_profit': gambling_pr + (self.br_bet - self.br_holiday_points_used[i])}, self.bot.query.user == p)
                            if self.br_holiday_points_used[i] > 0:
                                holiday_p = main_db.get(self.bot.query.user == p)['holiday']
                                main_db.update({'holiday': holiday_p + self.br_holiday_points_used[i]}, self.bot.query.user == p)
                                main_db.update({'balance': balance_p + self.br_bet - self.br_holiday_points_used[i]}, self.bot.query.user == p)
                            else:
                                main_db.update({'balance': balance_p + self.br_bet}, self.bot.query.user == p)
                        except Exception as e:
                            await self.bot.post_error(context, 'Could not refund bet to ' + context.message.author.name + '.', config.additional_error_message)
                            log.exception(e)
                else:
                    # _self.br_participants_ is now filled with usernames
                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** Ladies and gentlemen, the battle royale is about to begin. ' + str(len(self.br_participants)) + ' brave fighters have stepped into the arena after ' + context.message.author.name + ' called for a grand battle. They fight over ' + str(self.br_pool) + ' ' + config.currency_name + 's. Additionally, at least 1 ' + config.currency_name + ' is granted for each kill on the field. Good luck! :drum:')

                    dim_participants = self.br_participants[:]
                    kill_map = defaultdict(int)
                    time_intervals = [10, 12, 14, 16, 18, 20]
                    weapons = {}
                    last_killer = ''
                    streak = 0

                    for p in self.br_participants:
                        if p in self.custom_weapons:
                            weapons[p] = self.custom_weapons[p]
                        else:
                            weapons[p] = random.choice(weapon_emotes)

                    p_suicide = self.p_suicide
                    p_block = self.p_block
                    p_bomb_or_melee = self.p_bomb_or_melee
                    p_exotic = self.p_exotic
                    local_longest_streak = 0
                    local_longest_streak_user = None

                    while len(dim_participants) > 1:
                        await asyncio.sleep(random.choice(time_intervals))

                        if len(dim_participants) > 3:
                            max_killed = math.ceil(len(dim_participants)/3)
                            amnt_probabilities = [0.5]
                            amnt_list = []

                            for i in range(1, max_killed):
                                amnt_list.append(i)
                                amnt_probabilities.append(0.5 / (max_killed - 1))

                            amnt_list.append(max_killed)

                            x = random.uniform(0, 1)
                            cum_prob = 0

                            for i, i_p in zip(amnt_list, amnt_probabilities):
                                cum_prob += i_p

                                if x < cum_prob:
                                    break

                            amnt_killed = i
                        else:
                            amnt_killed = 1

                        for i in range(0, amnt_killed):
                            killed = random.choice(dim_participants)
                            event = random.uniform(0, 1)

                            if event < p_suicide:
                                if killed in self.custom_suicides:
                                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** ' + killed + ' ' + self.custom_suicides[killed])
                                else:
                                    suicide_emote = random.choice(self.suicide_emotes)
                                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** ' + killed + ' ' + suicide_emote + ' ' + killed)

                                killed = dim_participants.pop(dim_participants.index(killed))
                                continue

                            killer = killed

                            while killed == killer:
                                killer = random.choice(dim_participants)

                            if event < (1-p_block + p_suicide):
                                killed = dim_participants.pop(dim_participants.index(killed))

                                kill_map[killer] += 1

                                notes = []

                                if event < (p_suicide + p_bomb_or_melee):
                                    if event < ((p_suicide + p_bomb_or_melee) / 2):
                                        weapon = ':bomb:'
                                        notes.append('Bomb kill bonus: 1')
                                    else:
                                        weapon = ':right_facing_fist:'
                                        notes.append('Melee kill bonus: 1')

                                    kill_map[killer] += 1
                                elif event < p_suicide + p_bomb_or_melee + p_exotic:
                                    weapon = random.choice(self.exotic_weapons)
                                    notes.append('Exotic kill bonus: 10')
                                    kill_map[killer] += 10
                                else:
                                    weapon = weapons[killer]

                                if last_killer == killer:
                                    streak += 1
                                    kill_map[killer] += streak
                                    notes.append('Streak bonus: ' + str(streak))

                                    if streak > local_longest_streak:
                                        local_longest_streak = streak
                                        local_longest_streak_user = killer
                                else:
                                    if streak > 1 and killed == last_killer:
                                        notes.append('Shutdown bonus: 1')
                                        kill_map[killer] += 1

                                    streak = 1
                                    last_killer = killer

                                result = '**[BATTLE ROYALE]** ' + killer + ' ' + weapon + ' ' + killed

                                for note in notes:
                                    result += ' *(' + note + ')*'

                                await self.bot.post_message(self.bot.bot_channel, result)
                            else:
                                await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** ' + killer + ' :shield: ' + killed)

                    await self.bot.post_message(self.bot.bot_channel, '**[BATTLE ROYALE]** :confetti_ball: :confetti_ball: :confetti_ball: ' + dim_participants[0] + ' wins, taking home the pool of ' + str(self.br_pool) + ' ' + config.currency_name + 's! :confetti_ball: :confetti_ball: :confetti_ball:')

                    result = '```Scoreboard ' + linesep + linesep

                    indent = max(len(p) for p in self.br_participants)

                    ctr = 1
                    kill_map[dim_participants[0]] += self.br_pool

                    for p, k in sorted(kill_map.items(), key=itemgetter(1), reverse=True):
                        result += p.ljust(indent) + '   ' + str(k) + linesep
                        ctr += 1

                    for p in self.br_participants:
                        if p not in kill_map:
                            result += p.ljust(indent) + '   0' + linesep
                            ctr += 1

                    result += '```'
                    await self.bot.post_message(self.bot.bot_channel, result)
                    kill_map[dim_participants[0]] -= self.br_pool

                    # Update winner balance
                    try:
                        balance_first = main_db.get(self.bot.query.user == dim_participants[0])['balance']
                        main_db.update({'balance': balance_first + self.br_pool}, self.bot.query.user == dim_participants[0])
                    except Exception as e:
                        await self.bot.post_error(context, 'Could not update winner\'s balance.', config.additional_error_message)
                        log.exception(e)

                    # Update winner stats
                    try:
                        gambling_profit_first = main_db.get(self.bot.query.user == dim_participants[0])['gambling_profit']
                        main_db.update({'gambling_profit': gambling_profit_first + self.br_pool}, self.bot.query.user == dim_participants[0])
                        first_total_won = main_db.get(self.bot.query.user == dim_participants[0])['br_winnings']
                        main_db.update({'br_winnings': first_total_won + self.br_pool}, self.bot.query.user == dim_participants[0])
                    except Exception as e:
                        await self.bot.post_error(context, 'Could not update winner\'s gambling stats.', config.additional_error_message)
                        log.exception(e)

                    # Kills
                    try:
                        highest_total_owned = trivia_table.get(self.bot.query.name == 'highest_total_owned')['value']

                        for p in self.br_participants:
                            amnt_kills = kill_map[p]

                            if amnt_kills > 0:
                                try:
                                    balance = main_db.get(self.bot.query.user == p)['balance']
                                    main_db.update({'balance': balance + amnt_kills}, self.bot.query.user == p)
                                except Exception as e:
                                    await self.bot.post_error(context, 'Could not update balance for user ' + p + '.', config.additional_error_message)
                                    log.exception(e)

                                gambling_profit = main_db.get(self.bot.query.user == p)['gambling_profit']
                                main_db.update({'gambling_profit': gambling_profit + amnt_kills}, self.bot.query.user == p)

                                if amnt_kills > self.br_bet or p == dim_participants[0]:
                                    total_won = main_db.get(self.bot.query.user == p)['br_winnings']
                                    main_db.update({'br_winnings': total_won + amnt_kills - self.br_bet}, self.bot.query.user == p)

                                akills = main_db.get(self.bot.query.user == p)['br_score']
                                main_db.update({'br_score': akills + amnt_kills}, self.bot.query.user == p)

                                new_balance = balance + amnt_kills

                                if new_balance > highest_total_owned:
                                    trivia_table.update({'value': new_balance, 'person1': p, 'person2': 'None', 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, self.bot.query.name == 'highest_total_owned')
                                    highest_total_owned = new_balance
                    except Exception as e:
                        await self.bot.post_error(context, 'Could not update some stats/balances.', config.additional_error_message)
                        log.exception(e)

                    # Other
                    try:
                        maxkills = max(kill_map.items(), key=itemgetter(1))
                        trivia_table.update(increment('value'), self.bot.query.name == 'amnt_brs')
                        main_db.update(increment('br_wins'), self.bot.query.user == dim_participants[0])

                        highest_br_pool = trivia_table.get(self.bot.query.name == 'highest_br_pool')['value']
                        largest_br = trivia_table.get(self.bot.query.name == 'largest_br')['value']
                        most_kills = trivia_table.get(self.bot.query.name == 'most_br_score')['value']
                        longest_streak = trivia_table.get(self.bot.query.name == 'longest_streak')['value']

                        if maxkills[1] > most_kills:
                            trivia_table.update({'value': maxkills[1], 'person1': maxkills[0], 'person2': dim_participants[0], 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, self.bot.query.name == 'most_br_score')

                        if self.br_pool > highest_br_pool:
                            trivia_table.update({'value': self.br_pool, 'person1': dim_participants[0], 'person2': kill_map[dim_participants[0]], 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, self.bot.query.name == 'highest_br_pool')

                        if local_longest_streak > longest_streak:
                            trivia_table.update({'value': local_longest_streak, 'person1': local_longest_streak_user, 'person2': dim_participants[0], 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, self.bot.query.name == 'longest_streak')

                        if len(self.br_participants) > largest_br:
                            trivia_table.update({'value': len(self.br_participants), 'person1': dim_participants[0], 'person2': kill_map[dim_participants[0]], 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, self.bot.query.name == 'largest_br')
                    except Exception as e:
                        await self.bot.post_error(context, 'Could not update some battle royale stats (only affects !trivia output).', config.additional_error_message)
                        log.exception(e)

                    try:
                        for p in self.br_participants:
                            main_db.update(increment('brs'), self.bot.query.user == p)
                    except Exception as e:
                        await self.bot.post_error(context, 'Could not update some battle royale stats (only affects !trivia output).', config.additional_error_message)
                        log.exception(e)
        except Exception as e:
            await self.bot.post_error(context, 'Oh no, something went wrong.', config.additional_error_message)
            log.exception(e)

        # Reset stuff
        self.br_closed = True
        self.br_pool = 0
        self.br_bet = 0
        self.br_participants = []
        self.br_holiday_points_used = []



def setup(bot):
    """Battle royale cog load."""
    bot.add_cog(BattleRoyale(bot))
    log.info("Battle royale cog loaded")
