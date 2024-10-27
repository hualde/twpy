import io
import json
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

class GoogleServices:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                       'https://www.googleapis.com/auth/drive.readonly']
        
        # Check if we're running on Heroku
        if 'DYNO' in os.environ:
            # If on Heroku, the credentials should be in an environment variable
            credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_json:
                self.service_account_info = json.loads(credentials_json)
            else:
                raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set!")
        else:
            # If not on Heroku, assume the credentials are in a file
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    self.service_account_info = json.load(f)
            else:
                raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS file not found!")

        self.creds = service_account.Credentials.from_service_account_info(
            self.service_account_info, scopes=self.SCOPES)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def get_first_pending_item(self, spreadsheet_id):
        try:
            sheet = self.sheets_service.spreadsheets()
            result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                        range=os.environ.get('SAMPLE_RANGE_NAME', 'X!A2:C')).execute()
            values = result.get('values', [])

            if not values:
                print('No data found.')
                return None

            for index, row in enumerate(values):
                if len(row) >= 2 and (len(row) == 2 or row[2].lower() == 'pendiente' or row[2].strip() == ''):
                    return {
                        'column_a': row[0],
                        'column_b': row[1],
                        'row_index': index + 2
                    }

            print('No pending items found.')
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_sheet_status(self, spreadsheet_id, row_index):
        try:
            range_name = f'X!C{row_index}'
            body = {
                'values': [['enviado']]
            }
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=range_name,
                valueInputOption='RAW', body=body).execute()
            print(f"{result.get('updatedCells')} cells updated.")
            return True
        except Exception as e:
            print(f"An error occurred while updating the sheet: {e}")
            return False

    def get_image_from_drive(self, file_name):
        try:
            query = f"name = '{file_name}' and '{os.environ.get('DRIVE_FOLDER_ID')}' in parents"
            results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print(f'No file found with name: {file_name}')
                return None

            file_id = items[0]['id']
            request = self.drive_service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

            file.seek(0)
            return file

        except Exception as e:
            print(f"An error occurred while fetching the image: {e}")
            return None