import pickle
import os.path
from typing import Optional

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials

SHEETS_SERVICE_NAME="sheets"
SHEETS_SERVICE_VERSION="v4"

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
    ]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1crLL2SMWrftJTDdvFedD64BvZJq0zUMgXxru-IGEDwE'
SAMPLE_RANGE_NAME = 'Class Data!A2:E'


class Spreadsheet(object):
    
    spreadsheet_id: str
    token_file: str
    secrets_file: str
    creds: Optional[Credentials]
    
    def __init__(self, spreadsheet_id: str, token_file: str = 'token.pkl', secrets_file:str = 'credentials.json'):
        self.spreadsheet_id = spreadsheet_id
        self.token_file = token_file
        self.secrets_file = secrets_file
        self.creds = None
        
    def connect(self):
        """Carry out oauth flow for connecting to google sheets API."""
        
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as f:
                self.creds = pickle.load(f)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.secrets_file, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'wb') as f:
                pickle.dump(self.creds, f)

        self.service = build(SHEETS_SERVICE_NAME, SHEETS_SERVICE_VERSION, credentials=self.creds)

        
    def append_sheet(self, range_name, values):
        
        result = self.service.spreadsheets().values()\
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name, 
                valueInputOption="RAW",
                body={'values':values}
            )\
            .execute()
            
        print(result.get('updatedCells'))
        
    def get_range(self, range_name):
        r = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=range_name)
        response = r.execute()
        return response
        
if __name__ == "__main__":
    sheet = Spreadsheet(spreadsheet_id="1qyC-mv6Z5e74wAxWikI1_MB8hbJbWwxiztD9YJPcWt4")
    print("Connect")
    sheet.connect()
    sheet.get_sheet(range_name="Interesting/Difficult Tasks!A2:C")
    print("Append")
    #sheet.append_sheet(range_name="TestSheet", values=[["hello","world"]])