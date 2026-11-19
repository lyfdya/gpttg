import re
from dataclasses import dataclass
from datetime import datetime, timedelta

WEEKDAYS = {'понедельник': 0, 'вторник': 1, 'среду': 2, 'среда': 2, 'четверг': 3, 'пятницу': 4, 'пятница': 4, 'субботу': 5, 'суббота': 5, 'воскресенье': 6}

@dataclass
class Event:
    title: str
    start: datetime
    end: datetime

class ParseError(ValueError):
    pass

def parse(text: str, now: datetime) -> Event:
    s = text.strip()
    if not s:
        raise ParseError('Напишите дату, время и название события.')
    dates = list(re.finditer(r'\b(?:послезавтра|завтра|сегодня|понедельник|вторник|среду|среда|четверг|пятницу|пятница|субботу|суббота|воскресенье)\b|(?<!\d)\d{1,2}\.\d{1,2}(?:\.\d{4})?(?!\d)', s, re.I))
    if len(dates) > 1:
        raise ParseError('Укажите одну дату.')
    target = now.date()
    if dates:
        value = dates[0].group().lower()
        if value in WEEKDAYS:
            delta = (WEEKDAYS[value] - now.weekday()) % 7
            target += timedelta(days=delta or 7)
        elif value in ('сегодня', 'завтра', 'послезавтра'):
            target += timedelta(days={'сегодня': 0, 'завтра': 1, 'послезавтра': 2}[value])
        else:
            parts = [int(x) for x in value.split('.')]
            try:
                target = target.replace(year=parts[2] if len(parts) == 3 else now.year, month=parts[1], day=parts[0])
                if len(parts) == 2 and target < now.date():
                    target = target.replace(year=now.year + 1)
            except ValueError:
                raise ParseError('Не удалось понять дату. Пример: 25.11.2026.')
        s = s[:dates[0].start()] + ' ' + s[dates[0].end():]
    duration = timedelta(hours=1)
    duration_matches = list(re.finditer(r'\b(?:на\s+)?(полтора|полчаса|\d+|один|одна|два|две|три|четыре)\s*(час(?:а|ов)?|ч(?:ас)?\.?|минут(?:а|ы)?|мин\.?)\b|\bполчаса\b', s, re.I))
    if len(duration_matches) > 1:
        raise ParseError('Укажите продолжительность одним числом, например 90 минут.')
    if duration_matches:
        m = duration_matches[0]
        if m.group().lower() == 'полчаса':
            minutes = 30
        else:
            n = m.group(1).lower()
            number = {'полтора': 1.5, 'один': 1, 'одна': 1, 'два': 2, 'две': 2, 'три': 3, 'четыре': 4}.get(n)
            if number is None: number = int(n)
            minutes = int(number * (1 if m.group(2).lower().startswith('мин') else 60))
        if not 1 <= minutes <= 1440:
            raise ParseError('Продолжительность должна быть от 1 минуты до 24 часов.')
        duration = timedelta(minutes=minutes)
        s = s[:m.start()] + ' ' + s[m.end():]
    times = list(re.finditer(r'(?<![\w\d])(?:в\s*)?(\d{1,2})(?::(\d{2}))?(?![\w\d.:])', s, re.I))
    if len(times) != 1:
        raise ParseError('Укажите одно время, например 17:00 или 17. Если в названии есть число, напишите время через двоеточие и уберите другие числа.')
    m = times[0]
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    if hour > 23 or minute > 59:
        raise ParseError('Проверьте время: например, 17:00.')
    start = datetime.combine(target, datetime.min.time(), tzinfo=now.tzinfo).replace(hour=hour, minute=minute)
    if not dates and start <= now:
        start += timedelta(days=1)
    if dates and start <= now:
        raise ParseError('Это время уже прошло. Укажите будущую дату и время.')
    title = (s[:m.start()] + ' ' + s[m.end():]).strip(' ,;-—')
    title = re.sub(r'^\s*(?:в|на)\s+', '', title, flags=re.I)
    title = re.sub(r'\s+', ' ', title).strip(' ,;-—')
    if not title:
        raise ParseError('Добавьте название события, например: завтра 17:00 встреча с Максимом.')
    return Event(title, start, start + duration)
