import pytz
import sys
import os
import requests as req
from datetime import datetime
from icalendar import Calendar, Event

DAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']

EMAIL = os.environ['EMAIL']

CLASS_DESC_FIELDS = [
    (lambda json: json['discipline'], 'Предмет'),
    (lambda json: json.get('type', '?'), 'Тип'),
    (lambda json: json['lecturer_profiles'][0]['full_name'], 'Преподаватель')
]


def abbreviate(string: str, is_type=False):
    if len(string.split(' ')) > 4: return string
    if len(string.split(' ')) == 1 and not is_type:
        return string[:3]
    result_parts = ['']
    for part in string.split(' '):
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
    result = ' '.join(result_parts).strip()
    return result


class Class:
    name: str = None
    type: str = None
    desc = None
    location = None
    beg_time = None
    end_time = None

    def __init__(self, json: dict):
        self.name = json['discipline']
        if '(' in self.name:
            self.name = self.name[:self.name.find('(')].strip()
        self.type = json.get('type', '?')
        self.desc = ''
        for (field_fn, field_name) in CLASS_DESC_FIELDS:
            self.desc += f'{field_name}: {field_fn(json)}\n'
        self.desc += '\n\n# ' + str(datetime.now(tz=pytz.timezone('Europe/Moscow')))
        self.location = json['auditorium']
        self.beg_time = datetime.fromisoformat(json['date_start'])
        self.end_time = datetime.fromisoformat(json['date_end'])

    def get_summary(self):
        return f'[{abbreviate(self.type, True)}] {abbreviate(self.name)} {self.location}'

    def to_event(self):
        ev = Event()
        ev.add('summary', self.get_summary())
        ev.add('description', self.desc)
        ev.add('dtstart', self.beg_time)
        ev.add('dtend', self.end_time)
        return ev


def main():
    cal = Calendar()
    cal.add('prodid', '-//HSE Calendar//avevad.com//')
    cal.add('version', '2.0')
    result = req.get(f'https://api.hseapp.ru/v3/ruz/lessons?start={datetime.now().strftime("%Y-%m-%d")}&email={EMAIL}')
    for class_json in result.json():
        cl = Class(class_json)
        cal.add_component(cl.to_event())
    sys.stdout.buffer.write(cal.to_ical())
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
