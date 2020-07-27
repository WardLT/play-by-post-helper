"""Request a token file from Google to use Drive functionality"""
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# Get the data
cred_path = 'google-drive-creds.json'

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.appdata'
]


def main():
    """Shows basic usage of the Drive v3 API"""

    # Make sure the "google-drive-creds.json" file exists
    if not os.path.isfile(cred_path):
        raise ValueError('Credentials file missing. Make an app, enable the Drive API and download credentials '
                         f'to "{cred_path}"')

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10
    ).execute()
    assert results.get("kind", None) == "drive#fileList"
    print('It worked! You are ready to go!')


if __name__ == '__main__':
    main()
