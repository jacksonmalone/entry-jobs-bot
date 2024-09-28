# Entry Jobs Bot 🧑‍💻🤖
- A simple Discord bot to find (actual) entry level software developer jobs.  
- Uses the <a href="https://developer.adzuna.com/" target="_blank">Adzuna</a> job search API
- Built off of the <a href="https://discordpy.readthedocs.io/en/stable/index.html" target="_blank">discord.py</a> Python library
---
I built this out of my frustration with several job boards poor filters.  
The bot fetches the job postings, filtering out key words like "senior", "lead", "principal".  
Before the jobs are sent, I added a regex to filter out jobs that ask for 3 or more years of experience anywhere in the job description.  
I am working on adding more filters to make sure no jobs that aren't actual entry level jobs get through.
