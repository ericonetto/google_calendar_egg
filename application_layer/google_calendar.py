import os
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
from pathlib import Path
from application_layer.helper import is_ip_in_authorized_ranges, get_atlassian_ip_ranges, get_ip_ranges



# Scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.events.owned']


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
config_file = os.path.join(secrets_folder, "secret_file_path.json")
accepted_ip_ranges_file = os.path.join(secrets_folder, "accepted_ip_ranges_file.json")
#accepted_ip_ranges_file.json example
"""
{
    "accepted_ip_ranges": [{"cidr": "123.456.789.123"}, {"cidr": "198.189.160.130"}]
}
"""

local_ips = get_ip_ranges(accepted_ip_ranges_file)
authorized_ip_ranges = get_atlassian_ip_ranges() + local_ips

# Function to get current events from Google Calendar
def request_authorization(apify_request, apify_app):
    # Get the IP address from the request
    
    incoming_ip = apify_request.headers.get('cf-connecting-ip')
    if incoming_ip ==None:
        incoming_ip =  apify_request.remote_addr
    if incoming_ip !=None:
        if not is_ip_in_authorized_ranges(incoming_ip, authorized_ip_ranges):
            return "Access denied.", 403

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
                    

                    return apify_app.redirect(authorization_url + f"&redirect_uri=http%3A%2F%2Flocalhost%3A{apify_request.environ.get('SERVER_PORT')}%2Fgoogle_calendar%2Fauthorize")
                
            else:
                return "Error, no client_secret_file_name! POST a Google secret file in the parameter 'file' on /client_secret endpoint"


def client_secret(apify_request): 

    # Get the IP address from the request
    incoming_ip = apify_request.headers.get('cf-connecting-ip')
    if incoming_ip ==None:
        incoming_ip =  apify_request.remote_addr
    if not is_ip_in_authorized_ranges(incoming_ip, authorized_ip_ranges):
        return "Access denied.", 403


    if os.path.exists(config_file):
        with open(config_file) as f:
            config = json.load(f)
        if "client_secret_file_name" in config:
            client_secret_file_name = config["client_secret_file_name"]
            return {"client_secret_file_name" : True}

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
    # Get the IP address from the request
    incoming_ip = apify_request.headers.get('cf-connecting-ip')
    if incoming_ip ==None:
        incoming_ip =  apify_request.remote_addr
    if not is_ip_in_authorized_ranges(incoming_ip, authorized_ip_ranges):
        return "Access denied.", 403


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


# Function to create an event on Google Calendar
def create_event(apify_request, event_name, start_date, end_date):
    # Get the IP address from the request
    incoming_ip = apify_request.headers.get('cf-connecting-ip')
    if incoming_ip ==None:
        incoming_ip =  apify_request.remote_addr
    if not is_ip_in_authorized_ranges(incoming_ip, authorized_ip_ranges):
        return "Access denied.", 403


    if os.path.exists(token_file):
        with open(token_file, 'r') as json_file:
            creds_json = json.load(json_file)

        if "token" in creds_json:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            service = build('calendar', 'v3', credentials=creds)
            
            event = {
                'summary': event_name,
                'start': {
                    'dateTime': start_date + 'T00:00:00',
                    'timeZone': 'Europe/Paris',
                },
                'end': {
                    'dateTime': end_date + 'T23:59:59',
                    'timeZone': 'Europe/Paris',
                },
            }
            
            # Insert the event into the user's calendar
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            return f"Event created: {created_event.get('htmlLink')}"
        else:
            return "Error, no token found in authorization! GET A authorization from /request_authorization endpoint"
    else:
        return "Error, not authrorized! GET A authorization from /request_authorization endpoint"


# Function to delete an event from Google Calendar
def delete_event(apify_request, event_id):
    # Get the IP address from the request
    incoming_ip = apify_request.headers.get('cf-connecting-ip')
    if incoming_ip ==None:
        incoming_ip =  apify_request.remote_addr
    if not is_ip_in_authorized_ranges(incoming_ip, authorized_ip_ranges):
        return "Access denied.", 403


    if os.path.exists(token_file):
        with open(token_file, 'r') as json_file:
            creds_json = json.load(json_file)

        if "token" in creds_json:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                service = build('calendar', 'v3', credentials=creds)

                try:
                    service.events().delete(calendarId='primary', eventId=event_id).execute()
                    return f"Event with ID '{event_id}' deleted successfully."
                except Exception as e:
                    return f"An error occurred: {str(e)}"
        else:
            return "Error, no token found in authorization! GET A authorization from /request_authorization endpoint"
    else:
        return "Error, not authrorized! GET A authorization from /request_authorization endpoint"

def get_upcoming_events(apify_request, upcoming_days=1):
    # Get the IP address from the request
    incoming_ip = apify_request.headers.get('cf-connecting-ip')
    
    if not is_ip_in_authorized_ranges(incoming_ip, authorized_ip_ranges):
        return "Access denied.", 403
    
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
            end_of_day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=int(upcoming_days))).isoformat()


            # Call Google Calendar API to get today's events
            events_result = service.events().list(
                calendarId='primary', timeMin=now, timeMax=end_of_day, singleEvents=True, orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        else:
            return "Error, no token found in authorization! GET A authorization from /request_authorization endpoint"
    else:
        return "Error, not authrorized! GET A authorization from /request_authorization endpoint"
                
