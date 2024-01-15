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

# Load config from config.yml
with open("config.yml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Config
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
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

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
        events = convertToObjects(events)
        events = find_upcoming_events(events)
        members = memberResult.get("values", [])
        members = convertToObjects(members)
        birthdays = find_birthdays(members, BIRTHDAY_DELTA)
        members = find_members_with_reminders(members)

        for event in events:
            email_body = build_html_template(event, birthdays)
            send_email(
                "Reminder: %s, %s" % (event["Type"], event["Date"]),
                email_body,
                [x["Email"] for x in members],
            )

        post_to_discord(events, birthdays)

    except HttpError as err:
        print(err)


# Converts plain arrays into objects with keys from the first row
def convertToObjects(values):
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
            print(birthday)
            today_datetime = datetime.datetime.combine(
                today, datetime.datetime.min.time()
            )
            print(today_datetime)
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
    response = requests.post(WEBHOOK_URL, data=json.dumps(data), headers=headers)
    if response.status_code == 204:
        print("Message posted successfully")
    else:
        print(f"Failed to post message, status code: {response.status_code}")


def build_html_template(event, birthdays):
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
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
    main()
