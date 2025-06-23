import os
import asyncio
import aiohttp
import discord
from discord.ext import commands, tasks
from discord import AllowedMentions
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN    = os.getenv("DISCORD_TOKEN")
XBL_KEY          = os.getenv("XBL_KEY")
GAMERTAG         = os.getenv("GAMERTAG")
CHANNEL_ID       = int(os.getenv("CHANNEL_ID"))
ROLE_ID          = int(os.getenv("ROLE_ID", 0))
MENTION_EVERYONE = os.getenv("MENTION_EVERYONE", "False") == "True"

# set up what kind of mentions we allow
allowed = AllowedMentions(everyone=MENTION_EVERYONE, roles=True)

# intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_presence(session, gamertag):
    url = f"https://xbl.io/api/v2/search/{gamertag}"
    headers = {"X-Authorization": XBL_KEY}
    async with session.get(url, headers=headers) as resp:
        resp.raise_for_status()
        data = await resp.json()
    people = data.get("people", [])
    if not people:
        raise ValueError(f"No results for '{gamertag}'")
    return people[0]

@bot.event
async def on_ready():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Logged in as {bot.user}. Starting 60s loop.")
    check_status.start()

@tasks.loop(seconds=60)
async def check_status():
    async with aiohttp.ClientSession() as sess:
        try:
            player = await fetch_presence(sess, GAMERTAG)
        except Exception as e:
            print(f"[{datetime.now():%H:%M:%S}] Fetch error: {e}")
            return

    online   = player.get("presenceState") == "Online"
    activity = player.get("presenceText") or "Idle"
    status   = f"{GAMERTAG} is {'online' if online else 'offline'} • {activity}"

    # build mention prefix if needed
    prefix = ""
    if online and activity != "Idle":
        if ROLE_ID:
            prefix = f"<@&{ROLE_ID}> "
        elif MENTION_EVERYONE:
            prefix = "@everyone "

    # timestamp down to the second
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")

    # send
    ch = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
    try:
        await ch.send(f"{timestamp}{prefix}{status}", allowed_mentions=allowed)
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Sent → {prefix}{status}")
    except discord.Forbidden:
        print(f"[{datetime.now():%H:%M:%S}] Forbidden: Missing send permission.")
    except Exception as e:
        print(f"[{datetime.now():%H:%M:%S}] Send error: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
