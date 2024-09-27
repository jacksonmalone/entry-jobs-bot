import os
from dotenv import load_dotenv
import requests
import discord
from discord.ext import commands
from discord.ext import tasks
import psycopg2
import urllib.parse
import signal
import sys
import webserver

load_dotenv()
ADZUNA_API_URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"
API_ID = os.getenv('APP_ID')
APP_KEY = os.getenv('APP_KEY')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
print("channel:", CHANNEL_ID)
BOT_TOKEN = os.getenv('BOT_TOKEN')
HOST = os.getenv('DB_HOST')
USER = os.getenv('DB_USER')
PASSWORD = os.getenv('DB_PASSWORD')
DATABASE = os.getenv('DB_NAME')
DATABASE_URL = os.getenv('DATABASE_URL')

def fetch_job_postings():
    params = {
        'app_id': API_ID,
        'app_key': APP_KEY,
        "results_per_page": 20,
        "what": "software",  # Customize search terms
        "what_and": "developer",
        "what_or": "engineer",
        "what_exclude": "senior lead director principal",
        "location0": "US",  # Customize location
        "location1": "Pennsylvania",
        "location2": "Allegheny County",
        "location3": "Pittsburgh",
        "max_days_old": 7,
        "category": "it-jobs",
        "sort_by": "date",
        "full_time": "1",
    }
    #response = requests.get(ADZUNA_API_URL, params=params)

    # Manually encode the parameters
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    # Complete URL
    full_url = f"{ADZUNA_API_URL}?{query_string}"

    # Send GET request to Adzuna API
    response = requests.get(full_url)

    # Raises HTTPError, if one occurs
    response.raise_for_status()

    if response.status_code == 200:
        print("Successfully fetched job postings:", response.status_code)
        return response.json()
    else:
        print("Failed to fetch job postings:", response.status_code)
        return None

def fetch_job_postings_location(location):
    params = {
        'app_id': API_ID,
        'app_key': APP_KEY,
        "results_per_page": 20,
        "what": "software",  # Customize search terms
        "what_or": "engineer developer",
        "what_exclude": "senior lead director principal sr",
        "where": location, # user input location in ! command
        "max_days_old": 7,
        "category": "it-jobs",
        "sort_by": "date",
        "full_time": "1",
        "contract": "1",
    }
    #response = requests.get(ADZUNA_API_URL, params=params)

    # Manually encode the parameters
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    # Complete URL
    full_url = f"{ADZUNA_API_URL}?{query_string}"

    # Send GET request to Adzuna API
    response = requests.get(full_url)

    # Raises HTTPError, if one occurs
    response.raise_for_status()

    if response.status_code == 200:
        print("Successfully fetched job postings:", response.status_code)
        return response.json()
    else:
        print("Failed to fetch job postings:", response.status_code)
        return None

def format_job_posting(job):
    title = job['title']
    location = job['location']['area'][-1]
    company = job['company']['display_name']
    description = job['description'][:200] + "..."  # Trim description for readability
    url = job['redirect_url']

    return f"**{title}** at **{company}**\n📍 {location}\n{description}\n[Apply here]({url})\n"


# Initialize the PostgreSQL connection globally
db_conn = None

# Initialize database connection
db_conn = psycopg2.connect(DATABASE_URL)

# Create table for posted jobs
def init_db():
    with db_conn.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posted_jobs (
                job_id VARCHAR(255) PRIMARY KEY
            )
        ''')
        db_conn.commit()

# Check if job ID exists in the database
def has_been_posted(job_id):
    with db_conn.cursor() as cursor:
        cursor.execute('SELECT 1 FROM posted_jobs WHERE job_id = %s', (job_id,))
        result = cursor.fetchone()
        return result is not None

# Add job ID to the database
def mark_as_posted(job_id):
    with db_conn.cursor() as cursor:
        cursor.execute('''
            INSERT INTO posted_jobs (job_id) VALUES (%s)
            ON CONFLICT (job_id) DO NOTHING
        ''', (job_id,))
        db_conn.commit()

print("about to initialize database!")
# Initialize database on startup
init_db()
print("init success!")

# Create intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize the bot with a command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

@tasks.loop(hours=24)  # Runs every 24 hours
async def fetch_and_post_jobs():
    await bot.wait_until_ready()  # Ensure bot is fully ready
    channel = bot.get_channel(CHANNEL_ID)
    print("channel:", channel)
    job_data = fetch_job_postings()
    if job_data:
        for job in job_data['results']:
            job_id = job['id']  # Assuming 'id' is the key for the job ID in the API response
            
            # Check if this job has already been posted
            if not has_been_posted(job_id):
                # Format the job posting and send it to the Discord channel
                job_post = format_job_posting(job)
                await channel.send(job_post)
                
                # Mark the job as posted in the database to avoid reposting
                mark_as_posted(job_id)

@bot.command(name='jobs') # Runs when user inputs command !jobs
async def get_jobs(ctx):
    job_data = fetch_job_postings()  # Fetch jobs from API
    if job_data:
        new_jobs_found = False  # Flag to track if new jobs are found
        for job in job_data['results']:
            job_id = job['id']
            if not has_been_posted(job_id):
                job_post = format_job_posting(job)
                await ctx.send(job_post)
                mark_as_posted(job_id)  # Mark the job as posted
                new_jobs_found = True  # Set flag to True if a new job is posted
                
        # Check if no new jobs were found
        if not new_jobs_found:
            await ctx.send("There are no new job listings at this time.")
    else:
        await ctx.send("Could not fetch job listings at this time.")

@bot.command(name="jobs")
async def fetch_jobs(ctx, location: str):
    await ctx.send(f"Looking for jobs in {location}...")

    # Call the get_jobs function with the provided location
    try:
        job_data = fetch_job_postings_location(location)
        if job_data and 'results' in job_data:
            for job in job_data['results']:
                job_post = format_job_posting(job)
                await ctx.send(job_post)
        else:
            await ctx.send(f"No jobs found for {location}.")
    except requests.exceptions.HTTPError as e:
        await ctx.send(f"Error fetching jobs: {str(e)}")

@bot.event
async def on_ready():
    fetch_and_post_jobs.start()

def close_db():
    global db_conn
    if db_conn:
        db_conn.close()
        db_conn = None

# This function will be triggered when you stop the bot (CTRL+C)
'''
def handle_shutdown(signal, frame):
    print("Shutting down... closing PostgreSQL connection.")
    close_db()  # Close the database connection before shutting down
    sys.exit(0)
'''

# Register the signal handler for graceful shutdown (CTRL+C or termination)
'''
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
'''

if __name__ == '__main__':
    webserver.keep_alive()
    bot.run(BOT_TOKEN)
