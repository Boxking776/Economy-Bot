# Economy-Bot
A discord bot - written in Python 3 - introducing an artificial economy to reward users with a virtual currency. These 'points' can in turn be given away to others or they can be gambled with in a variety of fun minigames.


##### About the code:
I (Scamp) am not 'actually' a python programmer and mostly self-taught, i.e. I read other people's code and Stack Overflow answers. That said, neither do I know much of the 'pythonic' ways, nor is it guaranteed that the bot executes flawlessly. There are some failsafe mechanisms, but the author(s) can in no way be held reliable for damage or inconveniences of any kind caused by usage of the bot.

I don't know what the python standard naming conventions/best practices are, and hence I do not follow them.

Everyone may feel free to fork the project to fix bugs or to add their own gambling minigames and other features.

##### How to install/run:
1. Clone this repository
2. Install dependencies: tinydb, discord.py
3. Fill in your info in bot.ini. The important fields are: bot_channel_id, token, main_server and optionally holiday_announcement_channel_id if using the holidays cog. All IDs are long integers you can get by right-clicking a channel or server in discord. You will get your token by creating a discord 'app'. More info on discordapp.com/developers/applications/me.
4. Fill in your info in Cogs/data/*. Appropriate examples are already given.
5. List your admins in bot.ini, as well as your subscriber role in the [Gambling] section if using the gambling cog. Admins are usernames separated by commas.
6. Run 'python3 . in the root directory.

##### Asserts:
- Stats cog must be loaded last
- Timed Events cog must be loaded first
- Holidays cog must be loaded before gambling minigames

##### Known issues:
- !trivia and !season outputs sometimes miss empty lines between cog outputs depending on the current database state and/or amount of loaded cogs
- If the bot is dead while it should be executing a timed task, the timed task will not be executed at all that day. Workaround: run a cronjob to restart the bot five minutes before the timed tasks are run.
- Race conditions: e.g. when !acceptduel is executed while duel is being canceled because it was accepted at the last moment. Needs proper locking/guarding. Probably applies to all minigames.
