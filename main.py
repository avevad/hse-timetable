import os.path
import re
import sys
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from icalendar import Calendar, Event

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

DAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']

SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
SCHEDULE_RANGES = os.environ['SCHEDULE_RANGES'].split(',')
SCHEDULE_COLUMN = int(os.environ['SCHEDULE_COLUMN'])
EXCLUDE_STRINGS = os.environ['EXCLUDE_STRINGS'].split(',')


class Class:
    name: str = None
    desc = None
    location = None
    beg_time = None
    end_time = None
    day = None

    def __init__(self, desc: str, day: int, time: str):
        self.name = re.findall('^.+$', desc, re.MULTILINE)[0]
        self.name = self.name.replace(']', '] ')
        self.desc = desc
        self.day = day
        location_match = re.compile('ауд\\. (\\w+)', re.MULTILINE | re.IGNORECASE).search(desc)
        if location_match is not None:
            self.location = location_match.group(1)
        time_beg, time_end = time.split('-')
        time_beg_h, time_beg_m = map(int, time_beg.replace(':', '.').split('.'))
        time_end_h, time_end_m = map(int, time_end.replace(':', '.').split('.'))
        self.beg_time = datetime(2023, 9, 4 + day, time_beg_h, time_beg_m, 0)
        self.end_time = datetime(2023, 9, 4 + day, time_end_h, time_end_m, 0)

    def get_informative_name(self):
        result_parts = ['']
        for part in self.name.split(' '):
            if len(part) == 0:
                continue
            if not part.isalpha():
                if len(result_parts[-1]) != 0:
                    result_parts.append('')
                result_parts[-1] += part
                result_parts.append('')
                continue
            if len(part) == 1:
                result_parts[-1] += part
            else:
                result_parts[-1] += part[0].upper()
        result = ' '.join(result_parts)
        if self.location is not None:
            result += ' ' + self.location
        return result

    def to_event(self):
        ev = Event()
        ev.add('summary', self.get_informative_name())
        ev.add('description', self.desc)
        ev.add('dtstart', self.beg_time)
        ev.add('dtend', self.end_time)
        ev.add('rrule', {
            'freq': 'weekly',
            'byday': DAYS[self.day]
        })
        return ev


def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('sheets', 'v4', credentials=creds)
        spreadsheets = service.spreadsheets()
        result = spreadsheets.get(spreadsheetId=SPREADSHEET_ID,
                                  ranges=SCHEDULE_RANGES,
                                  includeGridData=True).execute()
        sheet = result['sheets'][0]
        cal = Calendar()
        cal.add('prodid', '-//HSE Calendar//avevad.com//')
        cal.add('version', '2.0')
        for (day, data) in enumerate(sheet['data']):
            matrix = []
            beg_row = data['startRow']
            end_row = beg_row + len(data['rowData'])
            for row in data['rowData']:
                matrix_row = []
                for cell in row['values']:
                    if 'userEnteredValue' in cell:
                        matrix_row.append(cell['userEnteredValue']['stringValue'])
                    else:
                        matrix_row.append('')
                matrix.append(matrix_row)
            for merge in sheet['merges']:
                i0, i1 = merge['startRowIndex'], merge['endRowIndex']
                j0, j1 = merge['startColumnIndex'], merge['endColumnIndex']
                if i1 <= beg_row or end_row <= i0:
                    continue
                i0 -= beg_row
                i1 -= beg_row
                for i in range(i0, i1):
                    for j in range(j0, j1):
                        matrix[i][j] = matrix[i0][j0]
            schedule_descs = [matrix_row[SCHEDULE_COLUMN] for matrix_row in matrix]
            schedule_times = [matrix_row[1] for matrix_row in matrix]
            for (time, desc) in zip(schedule_times, schedule_descs):
                exclude = False
                for excl in EXCLUDE_STRINGS:
                    if excl in desc:
                        exclude = True
                        break
                if desc == '' or exclude:
                    continue
                cl = Class(desc, day, time)
                cal.add_component(cl.to_event())
        sys.stdout.buffer.write(cal.to_ical())
        sys.stdout.buffer.flush()
    except HttpError as err:
        print(err)


if __name__ == '__main__':
    main()
