# Sunday Dinner

A simple python script that reads from a Google sheet and reminds participants of upcoming dinners.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/kitschmensch/sundaydinner.git
   ```

2. Create a virtual environment:

   ```bash
   python3 -m venv venv
   ```

3. Activate the virtual environment:

   ```bash
   source venv/bin/activate
   ```

4. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `config.yml` file in the project root directory.

2. Set the following environment variables in the `config.yml` file:

- SCOPES: ["https://www.googleapis.com/auth/spreadsheets.readonly"]
- SPREADSHEET_ID: from spreadsheet URL
- EVENTS: "2024!A:H"
- MEMBERS: "Members!A:M"
- WEBHOOK_URL: "https://discord.com/api/webhooks/abc123"
- SMTP_EMAIL: "email@email.com"
- SMTP_PASSWORD: "password123"
- SMTP_PORT: 465
- SMTP_SERVER: "smtp.gmail.com"
- EMAIL_DEBUG: False
- BIRTHDAY_DELTA: 21

Replace `your-database-url` with the URL of your database and `your-api-key` with your API key.

## Running the Reminder Script on a Cron Job

To schedule the `reminders.py` script to run on a cron job, follow these steps:

1. Open the crontab file for editing:

   ```bash
   crontab -e
   ```

2. Add the following line to the crontab file:

   ```plaintext
   * * * * * /path/to/python /path/to/sundaydinner/reminders.py
   ```

   Replace `/path/to/python` with the path to your Python executable and `/path/to/sundaydinner/reminders.py` with the full path to the `reminders.py` script.

3. Save and exit the crontab file.

The `reminders.py` script will now run at the specified interval as per the cron job configuration.
