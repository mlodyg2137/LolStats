# stats/services.py

from .models import (Match, Participant, Summoner, Champion, Queue, SummonerChampion)
from .utils import (get_match_ids_by_puuid, get_match_by_id, get_champions, get_queues, get_summoner_info_by_puuid, get_queues_info_by_summoner_id, RateLimitException)
from django.utils import timezone
from datetime import datetime
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP


MATCHES_LIMIT = 60
GAME_MODE_TO_NAME = {
    "5v5 Ranked Solo games": "Solo/Duo",
    "5v5 Ranked Flex games": "Flex",
    "5v5 Blind Pick games": "Blind Pick",
    "5v5 ARAM games": "ARAM",
    "SWIFTPLAY": "Swiftplay",
}


def save_champions():
    try:
        champions = get_champions()
        if champions:
            for champ, data in champions.get('data').items():
                champ_obj, created = Champion.objects.get_or_create(
                    key=data.get('key'),
                    name=data.get('name'),
                    icon=f"https://ddragon.leagueoflegends.com/cdn/15.11.1/img/champion/{data.get('image').get('full')}",
                )
    except Exception as e:
        print(e)


def save_queues():
    try:
        queues = get_queues()
        if queues:
            for data in queues:
                que_obj, created = Queue.objects.get_or_create(
                    queue_id = data.get('queueId'),
                    description = data.get('description'),
                )
    except Exception as e:
        print(e)


def save_recent_matches_for_summoner(summ: Summoner, force_get_data: bool = False) -> None:
    """
    Pobierz w pętlach kolejne porcje ID meczów od Riot API 
    (parametry: start=0,100,200…; count=100) aż API przestanie zwracać nowe.
    W bazie wstawi tylko te match_id, których jeszcze nie ma.
    """
    region = summ.region
    batch_size = 30
    start = 0

    while True:
        match_ids_chunk = get_match_ids_by_puuid(summ.puuid, region, count=batch_size, start=start)
        if not match_ids_chunk or start>=MATCHES_LIMIT:
            break
        for match_id in match_ids_chunk:
            match_obj, created = Match.objects.get_or_create(match_id=match_id, defaults={'game_duration': 0, 'timestamp': timezone.now()})
            if created or force_get_data:
                # Tylko jeżeli created=True, będziemy pobierać szczegóły z API
                match_data = get_match_by_id(match_id, region)
                if not match_data:
                    match_obj.delete()
                    continue

                info = match_data.get('info', {})

                # pobranie kolejki queue
                queue_type = info.get('queueType')  # np. "RANKED_SOLO_5x5" lub "RANKED_FLEX_SR"
                queue_obj, _ = Queue.objects.get_or_create(
                    queue_id=info.get('queueId'),
                    defaults={'description': queue_type}
                )
                match_obj.queue = queue_obj

                # Match API data
                game_mode = info.get('gameMode')
                game_duration = info.get('gameDuration', 0)
                game_start_timestamp = info.get('gameStartTimestamp', None)
                game_name = GAME_MODE_TO_NAME[queue_obj.description] if queue_obj.description in GAME_MODE_TO_NAME else queue_obj.description if queue_obj.description else game_mode
                if len(game_name)<=1 and queue_obj.queue_id == 480:
                    game_name="Quickplay"
                team_stats = dict()

                match_obj.game_mode = game_mode
                match_obj.game_name = game_name
                match_obj.game_duration = game_duration
                
                # Timestamp w API to liczba ms od 1.1.1970
                ts_ms = game_start_timestamp
                if ts_ms:
                    match_obj.timestamp = timezone.make_aware(datetime.fromtimestamp(ts_ms/1000.0))
                else:
                    match_obj.timestamp = timezone.now()
                
                # match_obj.save()

                summ_participation_holder = None
                participants = info.get('participants', [])
                for p in participants:
                    if p.get('puuid') == summ.puuid:
                        summ_participation_holder = p
                    else:
                        k               = p.get('kills', 0)
                        d               = p.get('deaths', 0)
                        a               = p.get('assists', 0)
                        team_id         = p.get('teamId')

                        if team_id not in team_stats:
                            team_stats[team_id] = {'kills': k, 'deaths': d, 'assists': a}
                        else:
                            team_stats[team_id]['kills'] += k
                            team_stats[team_id]['deaths'] += d
                            team_stats[team_id]['assists'] += a
                    

                # dodawanie rozpatrywanego participant
                p = summ_participation_holder
                champion_key = p.get('championId')
                champ_obj = Champion.objects.get(key=champion_key)

                puuid_p         = p.get('puuid')
                champ           = champ_obj
                k               = p.get('kills', 0)
                d               = p.get('deaths', 0)
                a               = p.get('assists', 0)
                win             = p.get('win', False)
                team_id         = p.get('teamId')

                team_stats[team_id]['kills'] += k
                team_stats[team_id]['deaths'] += d
                team_stats[team_id]['assists'] += a

                lane            = p.get('lane')
                farm            = p.get('totalMinionsKilled', 0)
                damage_dealt    = p.get('totalDamageDealt', 0)
                wards           = p.get('wardsPlaced', 0)
                gold_earned     = p.get('goldEarned', 0)
                double_k        = p.get('doubleKills', 0)
                triple_k        = p.get('tripleKills', 0)
                quadra_k        = p.get('quadraKills', 0)
                penta_k         = p.get('pentaKills', 0)
                kp              = (k / team_stats[team_id]['kills']) if team_stats[team_id]['kills'] > 0 else 0

                try:
                    summ_part = Summoner.objects.get(puuid=puuid_p)
                except Summoner.DoesNotExist:
                    pass

                Participant.objects.create(
                    summoner=summ_part,
                    match=match_obj,
                    champion=champ,
                    team_id=team_id,
                    lane=lane,
                    kills=k,
                    deaths=d,
                    assists=a,
                    win=win,
                    farm=farm,
                    damage_dealt=damage_dealt,
                    wards=wards,
                    double_kills = double_k,
                    triple_kills = triple_k,
                    quadra_kills = quadra_k,
                    penta_kills = penta_k,
                    kill_participation = kp,
                    gold_earned = gold_earned,
                )

                # uzupelnienie pozostalych statystyk meczu
                match_obj.team0_kills = team_stats.get(100, 0).get('kills', 0)
                match_obj.team0_deaths = team_stats.get(100, 0).get('deaths', 0)
                match_obj.team0_assists = team_stats.get(100, 0).get('assists', 0)
                match_obj.team1_kills = team_stats.get(200, 0).get('kills', 0)
                match_obj.team1_deaths = team_stats.get(200, 0).get('deaths', 0)
                match_obj.team1_assists = team_stats.get(200, 0).get('assists', 0)

                match_obj.save()

        # następna strona:
        start += batch_size



from django.db.models import Avg, Sum, Count, F, Q
from .models import Summoner, Participant, Match

def recalculate_summoner_advanced_stats(summ: Summoner):
    """
    Pobiera wszystkie Participanty tego Summonera,
    dzieli na SoloQ vs FlexQ (na podstawie match.queue)
    i zapisuje wszystkie pole w Summoner (solo_*, flex_*).
    """

    # Q do filtrowania:
    from django.db.models import Q

    solo_q_filter = Q(match__queue__queue_id=420)  # 420 = SoloQ 5x5 ranked
    flex_q_filter = Q(match__queue__queue_id=440)  # 440 = FlexQ ranked

    # --- 1) SoloQ: sumy kills, deaths, assists, count meczów, sumy wards, sumy gold, sumy minions
    solo_queryset = Participant.objects.filter(summoner=summ).filter(solo_q_filter)

    solo_agg = solo_queryset.aggregate(
        total_kills=Sum('kills'),
        total_deaths=Sum('deaths'),
        total_assists=Sum('assists'),
        total_wards=Sum('wards'),
        total_gold=Sum('gold_earned'),
        total_farm=Sum('farm'),
        matches_count=Count('id')  # ile wierszy (meczów) w SoloQ
    )

    # --- 2) FlexQ
    flex_queryset = Participant.objects.filter(summoner=summ).filter(flex_q_filter)

    flex_agg = flex_queryset.aggregate(
        total_kills=Sum('kills'),
        total_deaths=Sum('deaths'),
        total_assists=Sum('assists'),
        total_wards=Sum('wards'),
        total_gold=Sum('gold_earned'),
        total_farm=Sum('farm'),
        matches_count=Count('id')
    )

    # --- 3) kda (podzielić przez zero → zabezpieczenie)
    if solo_agg['matches_count'] and solo_agg['total_deaths']:
        solo_kda = ((solo_agg['total_kills'] + solo_agg['total_assists']) / solo_agg['total_deaths']) if solo_agg['total_deaths'] > 0 else 0
    else:
        solo_kda = 0.0

    if flex_agg['matches_count'] and flex_agg['total_deaths']:
        flex_kda = ((flex_agg['total_kills'] + flex_agg['total_assists']) / flex_agg['total_deaths']) if flex_agg['total_deaths'] > 0 else 0 
    else:
        flex_kda = 0.0

    # --- 4) średnie vision (wards), gold_per_min, minions_per_min
    #    gold_per_min = total_gold / (suma czasu wszystkich matchów w minutach)
    #    minions_per_min = total_farm / (suma czasu matchów w minutach)

    solo_total_duration_secs = (
        Match.objects
        .filter(participant__summoner=summ)
        .filter(queue__description="5v5 Ranked Solo games")
        .aggregate(total=Sum('game_duration'))['total'] or 0
    )

    flex_total_duration_secs = (
        Match.objects
        .filter(participant__summoner=summ)
        .filter(queue__description="5v5 Ranked Flex games")
        .aggregate(total=Sum('game_duration'))['total'] or 0
    )

    # gold_per_min i minions_per_min:
    if solo_total_duration_secs:
        solo_gpm = (solo_agg['total_gold'] / (solo_total_duration_secs / 60)) if solo_total_duration_secs > 0 else 0
        solo_mpm = (solo_agg['total_farm'] / (solo_total_duration_secs / 60)) if solo_total_duration_secs > 0 else 0
    else:
        solo_gpm = 0
        solo_mpm = 0

    if flex_total_duration_secs:
        flex_gpm = (flex_agg['total_gold'] / (flex_total_duration_secs / 60)) if flex_total_duration_secs > 0 else 0
        flex_mpm = (flex_agg['total_farm'] / (flex_total_duration_secs / 60)) if flex_total_duration_secs > 0 else 0
    else:
        flex_gpm = 0
        flex_mpm = 0

    # --- 5) Wyznaczanie main_role: 

    solo_lane_counts = (
        solo_queryset
        .values('lane')
        .annotate(count=Count('lane'))
        .order_by('-count')
    )
    flex_lane_counts = (
        flex_queryset
        .values('lane')
        .annotate(count=Count('lane'))
        .order_by('-count')
    )

    solo_main_role = solo_lane_counts[0]['lane'] if solo_lane_counts else None
    flex_main_role = flex_lane_counts[0]['lane'] if flex_lane_counts else None

    # --- 6) pole w Summoner:
    summ.solo_kda = round(solo_kda, 2)
    summ.flex_kda = round(flex_kda, 2)

    summ.solo_main_role = solo_main_role
    summ.flex_main_role = flex_main_role

    summ.solo_vision_avg = (solo_agg['total_wards'] / solo_agg['matches_count']) if solo_agg['matches_count'] else 0.0
    summ.flex_vision_avg = (flex_agg['total_wards'] / flex_agg['matches_count']) if flex_agg['matches_count'] else 0.0

    summ.solo_gold_per_min = int(solo_gpm)
    summ.flex_gold_per_min = int(flex_gpm)

    summ.solo_minions_per_min = solo_mpm
    summ.flex_minions_per_min = flex_mpm

    summ.save()


def save_summoner_rank_info(summ: Summoner) -> None:
    summoner_info = get_summoner_info_by_puuid(summ.puuid, summ.server)
    summoner_id = summoner_info.get('id')
    icon_id = summoner_info.get('profileIconId')
    summoner_level = summoner_info.get('summonerLevel')

    solo_rank = None
    solo_wins = None
    solo_loses = None
    flex_rank = None
    flex_wins = None
    flex_loses = None

    data = get_queues_info_by_summoner_id(summoner_id, summ.server)
    for league in data:
        match league.get('queueType'):
            case "RANKED_SOLO_5x5":
                solo_rank = f"{league.get('tier', 'Unknown')} {league.get('rank', '')}"
                solo_wins = league.get('wins', 0)
                solo_loses = league.get('losses', 0)
            case "RANKED_FLEX_SR":
                flex_rank = f"{league.get('tier', 'Unknown')} {league.get('rank', '')}"
                flex_wins = league.get('wins', 0)
                flex_loses = league.get('losses', 0)
    
    summ.summoner_id = summoner_id
    summ.icon = f"https://ddragon.leagueoflegends.com/cdn/15.11.1/img/profileicon/{icon_id}.png"
    summ.summoner_level = summoner_level

    summ.rank_solo = solo_rank
    summ.solo_wins = solo_wins
    summ.solo_loses = solo_loses

    summ.rank_flex = flex_rank
    summ.flex_wins = flex_wins
    summ.flex_loses = flex_loses

    summ.save()


def recalculate_summoner_champions(summoner):
    # 1) Pobranie wszystkich Participant danego Summonera
    participants = Participant.objects.filter(summoner=summoner).select_related('champion')

    # 2) Grupowanie po champion_id
    stats = defaultdict(lambda: {
        'matches': 0,
        'wins': 0,
        'kills': 0,
        'deaths': 0,
        'assists': 0
    })

    for p in participants:
        cid = p.champion_id
        stats[cid]['matches'] += 1
        stats[cid]['wins'] += 1 if p.win else 0
        stats[cid]['kills'] += p.kills
        stats[cid]['deaths'] += p.deaths
        stats[cid]['assists'] += p.assists

    # 3) Usuń stare rekordy SummonerChampion dla tego summoner
    SummonerChampion.objects.filter(summoner=summoner).delete()

    # 4) Dla każdej grupy policz winratio i kda i wstaw nowe rekordy
    objects_to_create = []
    for champ_id, vals in stats.items():
        matches = vals['matches']
        wins = vals['wins']
        total_kills = vals['kills']
        total_deaths = vals['deaths'] if vals['deaths'] > 0 else 0  # liczymy 0 zgonów

        # Winratio w procentach (Decimal)
        winratio_val = (Decimal(wins) / Decimal(matches) * Decimal(100)).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        ) if matches else Decimal('0.00')

        # KDA = (kills + assists) / deaths (jeśli deaths == 0, dzielimy przez 1, by nie dzielić przez zero)
        denom = Decimal(total_deaths) if total_deaths else Decimal(1)
        kda_val = (Decimal(total_kills + vals['assists']) / denom).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        objects_to_create.append(
            SummonerChampion(
                summoner=summoner,
                champion_id=champ_id,
                matches_num=matches,
                winratio=winratio_val,
                kda=kda_val
            )
        )

    # 5) Masowe wstawienie
    if objects_to_create:
        SummonerChampion.objects.bulk_create(objects_to_create)