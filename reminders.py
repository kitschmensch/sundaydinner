import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime
import requests
import json
from smtplib import SMTP_SSL as SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yaml
import logging

# Load config from config.yml
with open("config.yml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Config
LOGGING_LEVEL = config["LOGGING_LEVEL"]
SCOPES = config["SCOPES"]
SPREADSHEET_ID = config["SPREADSHEET_ID"]
EVENTS = config["EVENTS"]
MEMBERS = config["MEMBERS"]
WEBHOOK_URL = config["WEBHOOK_URL"]
SMTP_EMAIL = config["SMTP_EMAIL"]
SMTP_PASSWORD = config["SMTP_PASSWORD"]
SMTP_PORT = config["SMTP_PORT"]
SMTP_SERVER = config["SMTP_SERVER"]
EMAIL_DEBUG = config["EMAIL_DEBUG"]
BIRTHDAY_DELTA = config["BIRTHDAY_DELTA"]
SPREADSHEET_URL = config["SPREADSHEET_URL"]


def main():
    logging.basicConfig(
        filename="applog.txt",
        level=LOGGING_LEVEL,
        format="%(asctime)s %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing credentials")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            logging.info("Saving credentials")
            token.write(creds.to_json())

    logging.info("Credentials valid. Fetching data from Google Sheets")
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        eventResult = (
            sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=EVENTS).execute()
        )
        memberResult = (
            sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=MEMBERS).execute()
        )
        events = eventResult.get("values", [])
        events = convert_to_objects(events)
        events = find_upcoming_events(events)
        members = memberResult.get("values", [])
        members = convert_to_objects(members)
        birthdays = find_birthdays(members, BIRTHDAY_DELTA)
        members = find_members_with_reminders(members)
        logging.info("Events found: %s", len(events))
        logging.info("Members with reminders found: %s", len(members))
        logging.info("Birthdays found: %s", len(birthdays))
        if events:
            for event in events:
                email_body = build_html_template(events, birthdays)
                send_email(
                    "Reminder: %s, %s" % (event["Type"], event["Date"]),
                    email_body,
                    [x["Email"] for x in members],
                )
            post_to_discord(events, birthdays)

    except HttpError as err:
        logging.error(err)


# Converts plain arrays into objects with keys from the first row
def convert_to_objects(values):
    if not values:
        return []
    headers = values[0]
    data_objects = []
    for row in values[1:]:
        row_extended = row + [None] * (len(headers) - len(row))
        data_objects.append(dict(zip(headers, row_extended)))
    return data_objects


# Returns all date records that are N days away (default 2)
def find_upcoming_events(eventRecordArray, delta=2):
    today = datetime.date.today()
    twoDays = today + datetime.timedelta(days=delta)
    twoDays = twoDays.strftime("%m/%d/%Y")
    return [x for x in eventRecordArray if x["Date"] == twoDays]


# Returns all members where the "Reminders" column is TRUE
def find_members_with_reminders(members):
    return [x for x in members if x["Reminders"] == "TRUE"]


# Returns all members with a birthday in the next N days (default 14)
def find_birthdays(data, delta=14):
    today = datetime.datetime.today().date()
    filtered_entries = []
    for member in data:
        if member["Birthday"]:
            birthday = datetime.datetime.strptime(member["Birthday"], "%m/%d/%Y")
            birthday = birthday.replace(year=today.year)
            today_datetime = datetime.datetime.combine(
                today, datetime.datetime.min.time()
            )
            difference = birthday - today_datetime
            if 0 <= difference.days <= delta:
                filtered_entries.append(member)
    return filtered_entries


def post_to_discord(events, birthdays):
    content_string = ""
    content_string += f"**Upcoming Events!**\n\n"
    for event in events:
        content_string += f"**{event['Type']}**: {event['Date']}\n"
        for key, value in event.items():
            if key not in ["Type", "Date"]:
                content_string += f"**{key}**: {value}\n"
    if birthdays:
        content_string += f"\n**Upcoming Birthdays!!**\n"
        for birthday in birthdays:
            content_string += f"{birthday['Full Name']} - {birthday['Birthday']}\n"

    data = {
        "content": content_string,
        "username": "Sunday Dinner Bot",
    }
    headers = {"Content-Type": "application/json"}
    logging.info("Posting message to Discord:")
    logging.info(data)
    response = requests.post(WEBHOOK_URL, data=json.dumps(data), headers=headers)
    if response.status_code == 204:
        logging.info("Successfully posted message to Discord")
    else:
        logging.error(f"Failed to post message, status code: {response.status_code}")
        logging.error(response.content)


def build_html_template(event, birthdays):
    logging.info("Building HTML template")
    logging.info(event)
    logging.info(birthdays)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    .container {{
        width: 100%;
        max-width: 600px;
        margin: auto;
        font-family: Arial, sans-serif;
    }}
    .event-table {{
        width: 100%;
        border-collapse: collapse;
    }}
    .event-table td {{
        border: 1px solid #ddd;
        padding: 8px;
    }}
    @media screen and (max-width: 600px) {{
        .event-table, .event-table tr, .event-table td {{
            display: block;
            width: 100%;
        }}
    }}
    </style>
    </head>
    <body>
    <div class="container">
        <h1>Upcoming Event!</h1>
        <table class="event-table">
            <tbody>"""

    for key, value in event.items():
        html_template += f"""
                <tr>
                    <td><strong>{key}</strong></td>
                    <td>{value}</td>
                </tr>"""

    html_template += f"""
            </tbody>
        </table>"""

    if birthdays:
        html_template += f"""
        <h2>Birthdays</h2>"""
        for birthday in birthdays:
            html_template += f"""
        <p>{birthday["Full Name"]} - {birthday["Birthday"]}</p>"""

    html_template += f"""    
        <p><a href="{SPREADSHEET_URL}">Visit the spreadsheet to make changes.</a></p>
    </div>
    </body>
    </html>
    """

    return html_template


def send_email(subject, body, to_emails):
    msg = MIMEMultipart()
    msg["From"] = SMTP_EMAIL
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        smtp = SMTP(SMTP_SERVER, SMTP_PORT)
        smtp.set_debuglevel(EMAIL_DEBUG)
        smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
        try:
            smtp.sendmail(SMTP_EMAIL, to_emails, msg.as_string())
        finally:
            smtp.quit()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    main()
