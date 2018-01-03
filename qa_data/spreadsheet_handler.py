
import logging
import httplib2
import os
import json

from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

logging.basicConfig(level='INFO')

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
        flags = None

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'QA Telegram Bot'

SPREADSHEET_ID = '1L_-zGLY4IJhdKiqkooS_vMMmls1fkWN3XtUHz5lzW0A'

def parse_questions(sheet):
    data = sheet['data']
    row_data = [k['rowData'] for k in data]
    values = [r for r in row_data]
    cell_data = [v['effectiveValue'] for v in values]
    logging.info('row_data length: %d' % len(row_data))
    logging.info('cell_data length: %d' % len(cell_data))
    #logging.info(json.dumps(sheets,sort_keys=True,indent=4))

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
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
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
        self.service = self.create_service()
        self.logger = logging.getLogger(__name__)

    def read_spreadsheet_data(self, spreadsheet_id):
        '''
        Returns data from spreadsheet
        '''
        ranges = ['A1:E30']
        include_grid_data = True
        request = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id,
                                                  ranges=ranges, includeGridData=include_grid_data)
        response = request.execute()
        self.logger.debug(response)
        return response

def main():
    api = API()
    spreadsheet = api.read_spreadsheet_data(SPREADSHEET_ID)
    questions = parse_questions(spreadsheet['sheets'][0])
    

if __name__ == '__main__':
    main()
