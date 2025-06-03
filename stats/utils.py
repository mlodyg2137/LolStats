# stats/utils.py

import requests
from django.conf import settings
from django.http import Http404


class RateLimitException(Exception):
    """Wyjątek sygnalizujący przekroczony limit zapytań do Riot API."""
    pass


HEADERS = { 
    "Origin": "https://developer.riotgames.com",
    "X-Riot-Token": settings.RIOT_API_KEY,
}

def get_summoner_by_name_and_tag(gameName: str, tagLine: str, region: str = 'europe') -> dict | None:
    base_url = f'https://{region.lower()}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}'
    response = requests.get(base_url, headers=HEADERS)
    match response.status_code:
        case 200:
            return response.json()
        case 404:
            raise Http404(f"Nie znaleziono summonera w bazie Riot API: {gameName}#{tagLine}")
        case 429:
            raise RateLimitException("Przekroczono limit zapytań do Riot API.")
        case _:
            raise Exception(f"Nieoczekiwany błąd Riot API: {response.status_code}")
    
def get_summoner_server(puuid: str) -> str | None:
    base_url = f'https://europe.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}'
    response = requests.get(base_url, headers=HEADERS)
    match response.status_code:
        case 200:
            return response.json().get('region')
        case 404:
            raise Http404(f"Nie ma takiego gracza na serwerze Riot API o puuid {puuid}.")
        case 429:
            raise RateLimitException("Przekroczono limit zapytań do Riot API.")
        case _:
            raise Http404(f"Nieoczekiwany błąd Riot API: {response.status_code}")

def get_match_ids_by_puuid(puuid: str, region: str, count: int = 100, start: int = 0) -> list[str]:
    """
    Pobiera ostatnie `count` ID meczów dla danego puuid (Summoner).
    Używa endpointu Match-V5: 
      GET https://<kontynent>.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}
    Zwraca listę stringów (match ID).
    """
    continent = region
    url = f"https://{continent}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {'start': start, 'count': count}
    response = requests.get(url, params=params, headers=HEADERS)
    match response.status_code:
        case 200:
            return response.json()
        case 404:
            raise Http404(f"Nie ma meczy na serwerze Riot API dla gracza o puuid {puuid}.")
        case 429:
            raise RateLimitException("Przekroczono limit zapytań. spróbuj za kilka minut.")
        case _:
            raise Http404(f"Nieoczekiwany błąd Riot API: {response.status_code}")


def get_match_by_id(match_id: str, region: str) -> dict | None:
    """
    Pobiera szczegóły meczu po jego match_id (string typu “EUW1_1234567890”).
    Używa endpointu Match-V5:
      GET https://<kontynent>.api.riotgames.com/lol/match/v5/matches/{match_id}
    Zwraca JSON z wszystkimi danymi meczu (participants, gameDuration, queueId, gameStartTimestamp itd.)
    """
    continent = region
    url = f"https://{continent}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    response = requests.get(url, headers=HEADERS)
    match response.status_code:
        case 200:
            return response.json()
        case 404:
            raise Http404("Nie ma takiego meczu na serwerze Riot API.")
        case 429:
            raise RateLimitException("Przekroczono limit zapytań. spróbuj za kilka minut.")
        case _:
            raise Exception(f"Nieoczekiwany błąd Riot API: {response.status_code}")


def get_summoner_info_by_puuid(puuid: str, server: str) -> dict | None:
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    response = requests.get(url, headers=HEADERS)
    match response.status_code:
        case 200:
            return response.json()
        case 404:
            raise Http404(f"Nie ma takiego gracza na serwerze Riot API o puuid {puuid}.")
        case 429:
            raise RateLimitException("Przekroczono limit zapytań. spróbuj za kilka minut.")
        case _:
            raise Exception(f"Nieoczekiwany błąd Riot API: {response.status_code}")


def get_queues_info_by_summoner_id(summoner_id: str, server: str) -> dict | None:
    url = f"https://{server}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    response = requests.get(url, headers=HEADERS)
    match response.status_code:
        case 200:
            return response.json()
        case 404:
            raise Http404(f"Nie ma takiego gracza na serwerze Riot API o summoner_id {summoner_id}.")
        case 429:
            raise RateLimitException("Przekroczono limit zapytań. spróbuj za kilka minut.")
        case _:
            raise Exception(f"Nieoczekiwany błąd Riot API: {response.status_code}")


def get_queues():
    """
    Pobiera wszystkie istniejące kolejki gier
    """
    url = "https://static.developer.riotgames.com/docs/lol/queues.json"
    response = requests.get(url)
    match response.status_code:
        case 200:
            print("Uzyskano kolejki z API.")
            return response.json()
        case 404:
            raise Exception("Pusty wynik żądania do Riot API Queues")
        case _:
            raise Exception(f"Nieoczekiwany błąd Riot API: {response.status_code}")


def get_champions():
    """
    Pobiera wszystkie istniejące postacie
    """
    url = "https://ddragon.leagueoflegends.com/cdn/15.11.1/data/en_US/champion.json"
    response = requests.get(url)
    match response.status_code:
        case 200:
            print("Uzyskano bohaterów z API.")
            return response.json()
        case 404:
            raise Exception("Pusty wynik żądania do Riot API Champions")
        case _:
            raise Exception(f"Nieoczekiwany błąd Riot API: {response.status_code}")