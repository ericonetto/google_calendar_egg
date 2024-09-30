import os
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
from pathlib import Path

# Scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


"""
def main():

  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "client_secret_912593566269-qrhq6jlg8en9idmgal2iprp8c7bg223c.apps.googleusercontent.com.json", SCOPES
      )

      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
"""


client_secret_file_name = ""
this_script_folder = os.path.dirname(__file__)
secrets_folder =  os.path.join(this_script_folder, "secrets")
Path(secrets_folder).mkdir(parents=True, exist_ok=True)


token_file = os.path.join(secrets_folder, "token.json")
config_file = os.path.join(secrets_folder, "config.json")

# Function to get current events from Google Calendar
def request_authorization(apify_app):
    creds = None
    # Load saved credentials from token.json
    if os.path.exists(token_file):

        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # If no valid credentials, ask user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:


            if os.path.exists(config_file):
                with open(config_file) as f:
                    config = json.load(f)
                if "client_secret_file_name" in config:
                    client_secret_file_name = config["client_secret_file_name"]


                    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file_name, SCOPES)
                    #creds = flow.run_local_server(port=0)
                    authorization_url, state = flow.authorization_url(
                        # Recommended, enable offline access so that you can refresh an access token without
                        # re-prompting the user for permission. Recommended for web server apps.
                        access_type='offline',
                        # Optional, enable incremental authorization. Recommended as a best practice.
                        include_granted_scopes='true',
                        # Optional, set prompt to 'consent' will prompt the user for consent
                        prompt='consent')
                    

                    return apify_app.redirect(authorization_url + "&redirect_uri=http%3A%2F%2Flocalhost%3A9000%2Fgoogle_calendar%2Fauthorize")
                
            else:
                return "Error, no client_secret_file_name! POST a Google secret file in the parameter 'file' on /client_secret endpoint"

                


def client_secret(apify_request): 

    if os.path.exists(config_file):
        with open(config_file) as f:
            config = json.load(f)
        if "client_secret_file_name" in config:
            client_secret_file_name = config["client_secret_file_name"]
            return {"client_secret_file_name" : True}
    else:
        return {"client_secret_file_name" : False, "message": "no config made! POST a Google secret file in the parameter 'file' on /client_secret endpoint"}

    if apify_request.method == 'POST':   
        f = apify_request.files['file'] 
        client_secret_file_name = os.path.join(secrets_folder, f.filename)
        f.save(client_secret_file_name) 

        config = {"client_secret_file_name": client_secret_file_name}

        # Write data to a JSON file
        with open(config_file, 'w') as f:
            json.dump(config, f)

        return {"success": True, "client_secret_file_name" :True}


def authorize(apify_request):
    client_secret_file_name = None
    if os.path.exists(config_file):
        with open(config_file) as f:
            config = json.load(f)
        if "client_secret_file_name" in config:
            client_secret_file_name = config["client_secret_file_name"]

    if not client_secret_file_name:
        return "Error, no client_secret_file_name! POST a Google secret file in the parameter 'file' on /client_secret endpoint"

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file_name, scopes = SCOPES)
    flow.redirect_uri =  apify_request.url_root + "google_calendar/authorize"

    authorization_response = apify_request.url.replace("http", "https")
    flow.fetch_token(
        authorization_response=authorization_response)
    
    creds_json = flow.credentials.to_json()

    # Save the credentials for the next run
    with open(token_file, "w") as token:
      token.write(creds_json)

    if "token" in creds_json:
        return "Authorized"
    else:
        return "Error"





def get_upcoming_events():

    if os.path.exists(token_file):
        with open(token_file, 'r') as json_file:
            creds_json = json.load(json_file)

        if "token" in creds_json:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())


            service = build('calendar', 'v3', credentials=creds)
            
            # Convert to the correct format
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()  # 'Z' will automatically be appended
            end_of_day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=4)).isoformat()


            # Call Google Calendar API to get today's events
            events_result = service.events().list(
                calendarId='primary', timeMin=now, timeMax=end_of_day, singleEvents=True, orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
                
