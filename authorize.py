from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
if __name__ == '__main__':
    if not Path('credentials.json').is_file():
        raise SystemExit('Скачайте OAuth credentials.json из Google Cloud в эту папку.')
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    credentials = flow.run_local_server(port=0)
    Path('token.json').write_text(credentials.to_json(), encoding='utf-8')
    print('Готово. token.json создан. Храните его в секрете.')
