from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.conf import settings
from django.core.paginator import Paginator
from django.urls import reverse
from .models import (Summoner, Participant, Champion, Queue, Match)
from .utils import (RateLimitException, get_summoner_by_name_and_tag, get_summoner_server)
from .services import (save_recent_matches_for_summoner, save_champions, save_queues, save_summoner_rank_info, recalculate_summoner_advanced_stats)


def home(request):
    """
    Strona główna: formularz, w którym wpisujesz nick (name) i region.
    Po wciśnięciu Submit przenosi Cię do /summoner/<name>/?region=<region>
    """

    if not Champion.objects.exists():
        save_champions()
    
    if not Queue.objects.exists():
        save_queues()
        
    
    if request.method == 'POST':
        gameName = request.POST.get('gameName').strip()
        tagLine = request.POST.get('tagLine').strip()
        region = request.POST.get('region', 'europe')
        if gameName and tagLine:
            base_url = f"/summoner/{gameName}/{tagLine}/"
            return redirect(f'{base_url}?region={region}')
    return render(request, 'stats/home.html')


def summoner_detail(request, gameName, tagLine):
    """
    1) Próba znalezienia w bazie Summonera (po 'name' i 'region').
    2) Jeśli nie ma – pobieramy z Riot API i zapisujemy do bazy.
    3) Jeśli API zwróci błąd (404), to rzucamy Http404.
    4) Wyświetlamy szablon z danymi Summonera.
    """
    region = request.GET.get('region', 'europe')

    try:
        summ = Summoner.objects.get(gameName__iexact=gameName,
                                    tagLine__iexact=tagLine,
                                    region=region)
    except Summoner.DoesNotExist:
        try:
            summ = Summoner.objects.get(gameName__iexact=gameName, tagLine__iexact=tagLine)
            region = summ.region
        except Summoner.DoesNotExist:
            try:
                data = get_summoner_by_name_and_tag(gameName, tagLine, region)
                if data:
                    server = get_summoner_server(data['puuid'])
                    summ = Summoner.objects.create(
                        puuid=data['puuid'],
                        gameName=data['gameName'],
                        tagLine=data['tagLine'],
                        region=region,
                        server=server,
                    )
                    save_summoner_rank_info(summ)
                    
            except Http404 as e:
                messages.error(request, "Nie ma takiego gracza na serwerze Riot API.")
                return redirect('home')
            except RateLimitException as e:
                messages.error(request, "Przekroczono limit zapytań do Riot API.")
                return redirect('home')
            except Exception as e:
                messages.error(request, f"Błąd: {e}")
                return redirect('home')
    
    try:
        if request.method == 'POST' and request.POST.get('update') == '1':
            Participant.objects.filter(summoner=summ).delete()

            save_recent_matches_for_summoner(summ, force_get_data=True)
            recalculate_summoner_advanced_stats(summ)

            url = reverse('summoner_detail', args=[summ.gameName, summ.tagLine])
            return HttpResponseRedirect(f"{url}?region={region}")

        if not Participant.objects.filter(summoner=summ).exists():
            print("NIE ISTNIEJE ZADEN PARTICIPANT")
            save_recent_matches_for_summoner(summ)
            recalculate_summoner_advanced_stats(summ)
        else:
            recalculate_summoner_advanced_stats(summ)
    except Http404 as e:
        messages.error(request, "Nie ma takiego gracza na serwerze Riot API.")
        return redirect('home')
    
    except RateLimitException as e:
        messages.error(request, "Przekroczono limit zapytań do Riot API.")
        return redirect('home')
    
    except Exception as e:
        messages.error(request, f"Błąd: {e}")
        return redirect('home')

    participants = Participant.objects.filter(summoner=summ).select_related('match').order_by('-match__timestamp')

    # Paginator – po 20 pozycji na stronę
    paginator = Paginator(participants, 20)

    # Numer aktualnej strony z GET:
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except:
        # Jeśli podano niepoprawny numer lub spoza zakresu, pokaż pierwszą stronę:
        page_obj = paginator.get_page(1)

    context = {
        'summoner': summ,
        'participants': participants,
        'paginator': paginator,
        'page_obj': page_obj,
        'region': region
    }

    return render(request, 'stats/summoner_detail.html', context)


def summoner_list(request):
    """
    Wyświetla paginowaną listę wszystkich Summonerów w bazie.
    """
    all_summoners = Summoner.objects.all().order_by('gameName', 'tagLine')
    paginator = Paginator(all_summoners, 30)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'stats/summoner_list.html', {'page_obj': page_obj})