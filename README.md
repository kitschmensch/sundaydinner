# Sunday Dinner

A simple python script that reads from a Google sheet and reminds participants of upcoming dinners or other events. The script should be set up with a cron job to run once daily.

The script will:

1. Pull all events from the event sheet and find any events that are 2 days from today
2. Find all members with birthdays in the next 21 days from the members sheet
3. Compose an HTML message with the event details and upcoming birthdays
4. Send an email reminder to all members where "Reminders = True"
5. Post a message in a Discord channel

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/kitschmensch/sundaydinner.git
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `config.yml` file in the project root directory. For your convenience, use the included `config.yml.example`.

2. Change the following environment variables in the `config.yml` file:

```
# Config
SCOPES: ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# https://docs.google.com/spreadsheets/d/{id_here}/edit#gid=548180339
SPREADSHEET_ID: "arsntienarst"
# Events sheet should at least have a Type and Date column. All other columns in the range will be added to the reminder text.
EVENTS: "2024!A:H"

#Members should have Full Name, Birthday, and Reminders columns
MEMBERS: "Members!A:M"

# Click on any channel and generate a webhook URL
WEBHOOK_URL: "https://discord.com/api/webhooks/*******"

SMTP_EMAIL: "example@example.com"
SMTP_PASSWORD: "password123"
SMTP_PORT: 465
SMTP_SERVER: "smtp.gmail.com"

# Will print messages to the console when sending an email
EMAIL_DEBUG: False

# To embed a hyperlink to the spreadsheet in reminders
SPREADSHEET_URL: "https://docs.google.com/spreadsheets/d/token/edit?usp=sharing"

# How far in advance to search for upcoming birthdays
BIRTHDAY_DELTA: 21

#Logging level:
LOGGING_LEVEL: INFO
```

## Running the Reminder Script on a Cron Job

For easy updates, use the `update_and_run.sh` bash script to fetch/merge changes from the repo and run the script. Using a cron job is an easy way to check daily for reminders.

1. Make the bash script executable

   ```bash
   chmod +x update_and_run.sh
   ```

2. Open the crontab file for editing:

   ```bash
   crontab -e
   ```

3. Add the following line to the crontab file to run the script daily at 5pm:

   ```plaintext
   0 17 * * * /bin/bash /home/user/update_and_run.sh
   ```

   Replace `/home/user/update_and_run.sh` with the full path to the `update_and_run.sh` script.

4. Save and exit the crontab file.
