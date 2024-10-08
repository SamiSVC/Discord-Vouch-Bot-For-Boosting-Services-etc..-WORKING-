import discord
from discord import app_commands
import json
import os
import sqlite3
from datetime import datetime
import base64

SUPPORT_URL = base64.b64encode("https://discord.gg/serverboostify".encode()).decode()

def load_config():
    with open("config.json", "r") as file:
        return json.load(file)

config = load_config()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

VOUCH_CHANNEL_ID = config["vouch_channel_id"]
EMBED_COLOR = int(config["embed_background_color"].replace('#', '0x'), 16)
ADMIN_USER_ID = config["admin_user_id"]

os.makedirs("vouches", exist_ok=True)

db_connection = sqlite3.connect("vouches.db")
db_cursor = db_connection.cursor()

db_cursor.execute('''
CREATE TABLE IF NOT EXISTS vouches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER,
    author_name TEXT,
    author_avatar TEXT,
    rating INTEGER,
    text TEXT,
    timestamp TEXT,
    guild_icon TEXT,
    guild_name TEXT
)
''')
db_connection.commit()

def load_vouches():
    try:
        with open("vouches/vouch_data.json", "r", encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_vouch_json(vouch_data):
    vouches = load_vouches()
    vouches.append(vouch_data)

    with open("vouches/vouch_data.json", "w", encoding='utf-8') as file:
        json.dump(vouches, file, ensure_ascii=False, indent=4)

def save_vouch_sql(vouch_data):
    try:
        db_cursor.execute('''
        INSERT INTO vouches (author_id, author_name, author_avatar, rating, text, timestamp, guild_icon, guild_name) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vouch_data['author_id'],
            vouch_data['author_name'],
            vouch_data['author_avatar'],
            vouch_data['rating'],
            vouch_data['text'],
            vouch_data['timestamp'],
            vouch_data['guild_icon'],
            vouch_data['guild_name']
        ))
        db_connection.commit()
    except Exception as e:
        print(f"Error saving vouch to SQL: {e}")

def save_vouch_html(vouch_data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    author_name_safe = vouch_data['author_name'].replace('#', '_')
    filename = f"vouch_{author_name_safe}_{timestamp}.html"
    filepath = os.path.join("vouches", filename)

    guild_name = vouch_data.get('guild_name', 'Unknown Guild')

    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Vouch by {vouch_data['author_name']}</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                background-color: #2C2F33;
                color: white;
                margin: 0;
                padding: 20px;
            }}
            .embed {{
                border: 1px solid #7289DA;
                border-radius: 8px;
                background-color: #23272A;
                padding: 20px;
                max-width: 600px;
                margin: auto;
            }}
            .embed-header {{
                display: flex;
                align-items: center;
                margin-bottom: 15px;
            }}
            .embed-header img {{
                border-radius: 50%;
                margin-right: 10px;
                width: 40px;
                height: 40px;
            }}
            .embed-header h2 {{
                margin: 0;
                font-size: 18px;
                color: #7289DA;
            }}
            .embed-field {{
                margin-bottom: 15px;
            }}
            .embed-field-name {{
                font-weight: bold;
                color: #99AAB5;
            }}
            .embed-footer {{
                display: flex;
                align-items: center;
                border-top: 1px solid #99AAB5;
                padding-top: 10px;
                color: #99AAB5;
                font-size: 12px;
            }}
            .embed-footer img {{
                border-radius: 50%;
                margin-right: 10px;
                width: 20px;
                height: 20px;
            }}
            .support-button {{
                background-color: #7289DA;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                text-decoration: none;
                font-size: 14px;
                margin-top: 10px;
                display: inline-block;
            }}
            .support-button:hover {{
                background-color: #5B6EAE;
            }}
        </style>
    </head>
    <body>
        <div class="embed">
            <div class="embed-header">
                <img src="{vouch_data['author_avatar']}" alt="Author Avatar">
                <h2>{vouch_data['author_name']}</h2>
            </div>
            <div class="embed-field">
                <div class="embed-field-name">Rating</div>
                <div class="rating">{"⭐" * vouch_data['rating']} ({vouch_data['rating']}/5)</div>
            </div>
            <div class="embed-field">
                <div class="embed-field-name">Vouch</div>
                <div>{vouch_data['text']}</div>
            </div>
            <div class="embed-footer">
                <img src="{vouch_data['guild_icon']}" alt="Server Icon">
                <div>{guild_name} | Vouch Services</div>
            </div>
            <a href="javascript:void(0)" class="support-button" onclick="window.open(atob('{SUPPORT_URL}'), '_blank');">Support</a>
        </div>
    </body>
    </html>
    """

    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(html_content)

@tree.command(name="vouch", description="Give a vouch rating with text")
@app_commands.describe(rating="Rating from 1 to 5 stars", text="Your vouch message")
async def vouch(interaction: discord.Interaction, rating: int, text: str):
    if interaction.channel.id != VOUCH_CHANNEL_ID:
        await interaction.response.send_message("This command can only be used in the specified vouch channel.", ephemeral=True)
        return

    if rating < 1 or rating > 5:
        await interaction.response.send_message("Rating must be between 1 and 5!", ephemeral=True)
        return

    embed = discord.Embed(title="Vouch Received", color=EMBED_COLOR)
    embed.add_field(name="Author", value=interaction.user.mention, inline=True)
    embed.add_field(name="Rating", value=f"{'⭐' * rating} ({rating}/5)", inline=True)
    embed.add_field(name="Vouch", value=text, inline=False)

    embed.set_thumbnail(url=interaction.user.avatar.url)

    guild_name = interaction.guild.name if interaction.guild else "Unknown Guild"
    if interaction.guild and interaction.guild.icon:
        embed.set_footer(text=f"{guild_name} | Vouch Services", icon_url=interaction.guild.icon.url)
    else:
        embed.set_footer(text=f"{guild_name} | Vouch Services")

    await interaction.response.send_message(embed=embed)

    vouch_data = {
        'author_id': interaction.user.id,
        'author_name': str(interaction.user),
        'author_avatar': interaction.user.avatar.url if interaction.user.avatar else '',
        'rating': rating,
        'text': text,
        'timestamp': str(datetime.now()),
        'guild_icon': interaction.guild.icon.url if interaction.guild and interaction.guild.icon else '',
        'guild_name': guild_name
    }
    save_vouch_json(vouch_data)
    save_vouch_sql(vouch_data)
    save_vouch_html(vouch_data)

@tree.command(name="vouches", description="See the list of vouches in the server")
async def vouches(interaction: discord.Interaction):
    db_cursor.execute("SELECT author_name, rating, text FROM vouches")
    vouches_data = db_cursor.fetchall()

    total_vouches = len(vouches_data)

    embed = discord.Embed(
        title="Vouch List",
        description=f"Total Vouches: {total_vouches}",
        color=EMBED_COLOR
    )

    for author_name, rating, text in vouches_data:
        embed.add_field(
            name=f"Vouch by {author_name}",
            value=f"Rating: {'⭐' * rating} ({rating}/5)\nMessage: {text}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

@tree.command(name="cleardatabase", description="Clears all vouches from the database (Admin Only)")
async def clear_database(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_USER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message("Are you sure you want to clear the database? (yes/no)", ephemeral=True)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30)
        if msg.content.lower() == 'yes':
            db_cursor.execute("DELETE FROM vouches")
            db_connection.commit()
            await interaction.followup.send("The database has been cleared.", ephemeral=True)
        else:
            await interaction.followup.send("Database clearing canceled.", ephemeral=True)
    except asyncio.TimeoutError:
        await interaction.followup.send("You took too long to respond. Database clearing canceled.", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {bot.user}')

@bot.event
async def on_shutdown():
    db_connection.close()

TOKEN = config["bot_token"]
bot.run(TOKEN)
