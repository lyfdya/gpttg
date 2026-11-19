import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from parser import parse, ParseError

class ParserTests(unittest.TestCase):
    def setUp(self): self.now = datetime(2026, 11, 19, 16, 0, tzinfo=ZoneInfo('Europe/Moscow'))
    def test_weekday_duration(self):
        e = parse('вторник 17:00 встреча с Максимом два часа', self.now)
        self.assertEqual((e.title, e.start.day, e.start.hour, (e.end-e.start).total_seconds()), ('встреча с Максимом', 24, 17, 7200))
    def test_next_time(self):
        self.assertEqual(parse('17 встреча', self.now).start.day, 19)
        self.assertEqual(parse('15 встреча', self.now).start.day, 20)
    def test_explicit_and_minutes(self):
        e = parse('25.11 15:30 врач на 30 минут', self.now)
        self.assertEqual((e.title, e.start.day, e.end.minute), ('врач', 25, 0))
    def test_ambiguous_and_past(self):
        for s in ('завтра встреча', 'сегодня 12:00 врач', 'завтра 17 18 встреча'):
            with self.subTest(s=s), self.assertRaises(ParseError): parse(s, self.now)

if __name__ == '__main__': unittest.main()
