import json
from urllib.error import URLError
from urllib.request import urlopen


SCOREBOARD_ENDPOINTS = (
    ('Futebol', 'https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/scoreboard'),
    ('NBA', 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'),
)


def _format_score(value):
    if value in (None, ''):
        return None
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value)


def _event_to_match(event, sport_name):
    competition = event.get('competitions', [{}])[0]
    competitors = competition.get('competitors', [])
    if len(competitors) < 2:
        return None

    home = next((item for item in competitors if item.get('homeAway') == 'home'), competitors[0])
    away = next((item for item in competitors if item.get('homeAway') == 'away'), competitors[1])
    status = event.get('status', {})
    status_type = status.get('type', {})
    state = status_type.get('state', 'pre')
    detail = status_type.get('shortDetail') or status_type.get('detail') or 'A confirmar'

    return {
        'league': sport_name,
        'home_team': home.get('team', {}).get('displayName', 'Mandante'),
        'away_team': away.get('team', {}).get('displayName', 'Visitante'),
        'home_score': _format_score(home.get('score')),
        'away_score': _format_score(away.get('score')),
        'status': detail,
        'is_live': state == 'in',
    }


def fetch_scoreboard():
    matches = []
    for sport_name, endpoint in SCOREBOARD_ENDPOINTS:
        sport_matches = []
        try:
            with urlopen(endpoint, timeout=3) as response:
                payload = json.load(response)
        except (OSError, URLError, ValueError):
            continue
        for event in payload.get('events', []):
            match = _event_to_match(event, sport_name)
            if match:
                sport_matches.append(match)
        matches.extend(sport_matches[:2])
    return matches[:4]