import discord
from discord.ext import commands
from discord import app_commands
from google.oauth2 import service_account
from googleapiclient.discovery import build
import matplotlib.pyplot as plt
import numpy as np
import io

# Keep-Alive for Replit
from keep_alive import keep_alive

# Discord Bot Token
DISCORD_BOT_TOKEN = 'TOKEN'  # Replace with your token

# Google Analytics Properties and JSON Credentials
GA_PROPERTIES = {
    'Leaderboard': {
        'property_id': '471303810',
        'credentials': 'absolute-nexus-446416-s9-885516aa860f.json'
    },
    'GambleAssist': {
        'property_id': '465958588',
        'credentials': 'gamble-assist-231452b6280e.json'
    }
}

# Google Analytics API Scope
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

# Initialize the Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Google Analytics Authentication
def get_ga_service(credentials_file):
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=SCOPES
    )
    return build('analyticsdata', 'v1beta', credentials=credentials)

# Fetch Analytics Data
def get_analytics_data(website, duration):
    if website not in GA_PROPERTIES:
        raise ValueError("Invalid website selected.")

    property_id = GA_PROPERTIES[website]['property_id']
    credentials_file = GA_PROPERTIES[website]['credentials']
    service = get_ga_service(credentials_file)

    if duration.endswith('m'):  # Handle months
        num_months = int(duration[:-1])
        start_date = f'{30 * num_months}daysAgo'
    else:  # Handle days
        num_days = int(duration)
        start_date = f'{num_days}daysAgo'

    request_body = {
        'dateRanges': [{'startDate': start_date, 'endDate': 'today'}],
        'metrics': [{'name': 'screenPageViews'}],
        'dimensions': [{'name': 'date'}]
    }

    response = service.properties().runReport(
        property=f'properties/{property_id}',
        body=request_body
    ).execute()

    result = []
    total_views = 0  # Variable to store total views
    for row in response.get('rows', []):
        date = row['dimensionValues'][0]['value']
        page_views = int(row['metricValues'][0]['value'])
        result.append((date, page_views))
        total_views += page_views  # Sum up the page views

    return result, total_views

# Generate Chart
def generate_chart(data):
    dates = [date for date, _ in data]
    views = [views for _, views in data]

    fig, ax = plt.subplots(figsize=(10, 6))
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    gradient = np.vstack((gradient, gradient))
    ax.imshow(gradient, aspect='auto', cmap='winter', extent=ax.get_xlim() + ax.get_ylim(), alpha=0.3)

    ax.plot(dates, views, marker='o', color='tab:blue', linestyle='-', linewidth=2, markersize=8)

    ax.set_xlabel('Date', fontsize=12, color='black')
    ax.set_ylabel('Page Views', fontsize=12, color='black')
    ax.set_title('Page Views Over Time', fontsize=14, color='black')

    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    ax.grid(True, linestyle='--', color='gray', alpha=0.5)

    img_bytes = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    return img_bytes

# Step 1: Choose Website
class WebsiteSelection(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='Leaderboard', style=discord.ButtonStyle.primary)
    async def leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✅ **Leaderboard selected!** Now choose a duration:",
            view=DurationSelection('Leaderboard'),
            ephemeral=True
        )

    @discord.ui.button(label='GambleAssist', style=discord.ButtonStyle.success)
    async def gambleassist(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✅ **GambleAssist selected!** Now choose a duration:",
            view=DurationSelection('GambleAssist'),
            ephemeral=True
        )

# Step 2: Choose Duration
class DurationSelection(discord.ui.View):
    def __init__(self, website):
        super().__init__()
        self.website = website

    @discord.ui.select(
        placeholder="Select a duration",
        options=[
            discord.SelectOption(label="1 Day", value="1"),
            discord.SelectOption(label="7 Days", value="7"),
            discord.SelectOption(label="28 Days", value="28"),
            discord.SelectOption(label="1 Month", value="1m"),
            discord.SelectOption(label="3 Months", value="3m")
        ]
    )
    async def select_duration(self, interaction: discord.Interaction, select: discord.ui.Select):
        duration = select.values[0]
        try:
            data, total_views = get_analytics_data(self.website, duration)
            chart_img = generate_chart(data)
            duration_text = f"{duration[:-1]} month(s)" if duration.endswith('m') else f"{duration} day(s)"

            embed = discord.Embed(
                title=f"📊 **{self.website} Analytics Data ({duration_text})**",
                description=f"Total Page Views: **{total_views}**",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(
                embed=embed,
                file=discord.File(chart_img, filename="analytics_chart.png")
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# Command Handler
@bot.tree.command(name="analytics", description="View analytics data with interactive menus")
async def analytics(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📊 Analytics Dashboard",
        description="Please select a website to view its analytics data.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Choose a website below:")
    await interaction.response.send_message(embed=embed, view=WebsiteSelection(), ephemeral=True)

# On Ready
@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}!')
    await bot.tree.sync()

# Keep the bot alive on Replit
keep_alive()
bot.run(DISCORD_BOT_TOKEN)
