import pytz
import sys
import os
import requests as req
from datetime import datetime, timedelta
from icalendar import Calendar, Event

DAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']

UID_SUFFIX = '@hse-sched.avevad.com'

EMAIL = os.environ['EMAIL']
SHORT = os.environ['SHORT']
DEBUG = os.environ['DEBUG']

CLASS_DESC_FIELDS = [
    (lambda json: json['discipline'], 'Предмет'),
    (lambda json: json.get('type', '?'), 'Тип'),
    (lambda json: json['lecturer_profiles'][0]['full_name'], 'Преподаватель')
]

SUBJECT_SHORTNAMES = {
    'Линейная алгебра и геометрия': 'Линал',
    'Математический анализ': 'Матан',
    'История России': 'История',
    'Язык программирования Python': 'Python',
    'Язык программирования C++': 'C++',
    'Алгоритмы и структуры данных': 'Алгосы',
    'Дискретная математика': 'Дискра',
    'Теория вероятностей': 'Теорвер',
    'Язык программирования Rust': 'Rust',
    'Архитектура компьютера': 'АКОС',
    'Операционные системы': 'АКОС',
    'Математическая статистика': 'Матстат',
    'Дифференциальные уравнения': 'Диффуры',
    'Функциональный анализ': 'Функан',
    'Комплексный анализ': 'Комплан',
    'Машинное обучение': 'ML',
    'Глубинное обучение': 'DL',
    'DevOps': 'DevOps',
    'Язык SQL': 'SQL',
}


def abbreviate(string: str, is_type=False, fallback_len=3):
    if len(string.split(' ')) > 4: return string
    if len(string.split(' ')) == 1 and not is_type:
        return string[:fallback_len]
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
    ruz_id: str = None
    name: str = None
    type: str = None
    desc = None
    auditorium = None
    location = None
    beg_time = None
    end_time = None
    init_time = None

    def __init__(self, json: dict):
        self.ruz_id = json["id"]
        self.name = json['discipline']
        if '(' in self.name:
            self.name = self.name[:self.name.find('(')].strip()
        self.type = json.get('type', '?')
        self.desc = ''
        for (field_fn, field_name) in CLASS_DESC_FIELDS:
            self.desc += f'{field_name}: {field_fn(json)}\n'
        self.auditorium = json['auditorium']
        
        self.location = f'{self.auditorium}'
        if 'building' in json:
            self.location += f', {json["building"]}'
        
        if SHORT == '0':
            self.desc += f'Аудитория: {self.auditorium}\n'

        if 'note' in json:
            self.desc += f'\nПримечание: {json["note"]}\n'

        self.init_time = datetime.now(tz=pytz.timezone('Europe/Moscow'))

        if DEBUG == '1':
            self.desc += f'\n\n# {self.init_time} #{self.ruz_id}'

        self.beg_time = datetime.fromisoformat(json['date_start'])
        self.end_time = datetime.fromisoformat(json['date_end'])

    def get_summary(self):
        if SHORT == '2':
            abbr_name = abbreviate(self.name, fallback_len=7)
            for key, value in SUBJECT_SHORTNAMES.items():
                if key in self.name:
                    abbr_name = value
                    break
            return f'[{abbreviate(self.type, True)}] {abbr_name} {self.auditorium}'
        elif SHORT == '1':
            return f'[{abbreviate(self.type, True)}] {abbreviate(self.name)} {self.auditorium}'
        else:
            return f'[{self.type}] {self.name}'

    def to_event(self):
        ev = Event()
        ev.add('summary', self.get_summary())
        ev.add('location', self.location)
        ev.add('uid', f'{self.ruz_id}{UID_SUFFIX}')
        ev.add('description', self.desc)
        ev.add('dtstart', self.beg_time)
        ev.add('dtend', self.end_time)
        ev.add('last-modified', self.init_time)

        return ev


def main():
    cal = Calendar()
    cal.add('prodid', '-//HSE Calendar//avevad.com//')
    cal.add('version', '2.0')
    start_time = datetime.now()
    start_time -= timedelta(days=start_time.weekday())
    result = req.get(f'https://api.hseapp.ru/v3/ruz/lessons?start={start_time.strftime("%Y-%m-%d")}&email={EMAIL}')
    for class_json in result.json():
        cl = Class(class_json)
        cal.add_component(cl.to_event())
    sys.stdout.buffer.write(cal.to_ical())
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
