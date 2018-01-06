
import logging
import httplib2
import os
import json

from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
        flags = None

def parse_questions(sheet):
    row_data = sheet['data'][0]['rowData'] # Array of rows
    data = []
    for row in row_data:
        cells = []
        if len(row) == 0:
            continue
        for cell in row['values']:
            if 'effectiveValue' in cell.keys():
                value = list(cell['effectiveValue'].values())
                cells.append([value[0]])
                if 'effectiveFormat' in cell.keys():
                    cells[-1].append(cell['effectiveFormat']['backgroundColor'])
            else:
                cells.append('')
        data.append(cells)
    return data

class API(object):
    
    def get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
        Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'sheets.googleapis.com-qa-telegram-bot.json')

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES)
            flow.user_agent = self.APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else: # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials


    def create_service(self):
        '''
        Creates a Sheets API Service Object
        '''
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
        service = discovery.build('sheets','v4', http=http,
                                  discoveryServiceUrl=discoveryUrl)
        return service
    
    def __init__(self):
        self.SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
        self.CLIENT_SECRET_FILE = 'client_secret.json'
        self.APPLICATION_NAME = 'QA Telegram Bot'
 
        self.service = self.create_service()
        self.logger = logging.getLogger(__name__)

    def read_spreadsheet_data(self, spreadsheet_id,ranges):
        '''
        Returns data from spreadsheet
        '''
        include_grid_data = True
        request = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id,
                                                  ranges=ranges, includeGridData=include_grid_data)
        response = request.execute()
        self.logger.debug(response)
        return response
