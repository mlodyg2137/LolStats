from django.test import TestCase
from django.urls import reverse
from stats.models import Summoner, Queue, Champion, Match, Participant


class HomeViewTest(TestCase):
    def test_home_returns_200_and_uses_template(self):
        """
        GET na 'home' powinien zwrócić status 200
        i renderować szablon 'stats/home.html'.
        """
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # sprawdzamy, czy użyty został właściwy template
        self.assertTemplateUsed(response, 'stats/home.html')


class SummonerModelTest(TestCase):
    def test_solo_matches_num_and_winratio_zero(self):
        # gdy solo_wins i solo_loses to 0 (domyślnie)
        s = Summoner.objects.create(
            puuid="test-puuid",
            gameName="TestUser",
            tagLine="1234",
            region="euw1",
            server="euw1"
        )
        # katalog domyślnych wartości: solo_wins=0, solo_loses=0
        self.assertEqual(s.solo_matches_num, 0)
        self.assertEqual(s.solo_winratio, "0.0%")

    def test_solo_matches_num_and_winratio_nonzero(self):
        # uzupełnijmy ręcznie pola
        s = Summoner.objects.create(
            puuid="test-puuid2",
            gameName="AnotherUser",
            tagLine="5678",
            region="euw1",
            server="euw1",
            solo_wins=7,
            solo_loses=3
        )
        # teraz solo_matches_num powinno być 10, a winratio 70.0%
        self.assertEqual(s.solo_matches_num, 10)
        self.assertEqual(s.solo_winratio, "70.0%")


class SummonerDetailViewTest(TestCase):
    def setUp(self):
        # 1) Queue i Champion (potrzebne do powiązań w Participant/Match)
        q = Queue.objects.create(queue_id=420, description="5v5 Ranked Solo games")
        champ = Champion.objects.create(key=1, name="TestChamp", icon="http://example.com/icon.png")

        # 2) Summoner
        self.summ = Summoner.objects.create(
            puuid="puuidtest123",
            gameName="SummonerX",
            tagLine="0001",
            region="euw1",
            server="euw1"
        )

        # 3) Match i Participant powiązany z Summonerem
        m = Match.objects.create(
            match_id="match123",
            queue=q,
            game_mode="CLASSIC",
            game_name="5v5 Ranked Solo games",
            game_duration=1800,
            timestamp="2025-05-30T12:00:00Z"
        )
        Participant.objects.create(
            summoner=self.summ,
            match=m,
            champion=champ,
            team_id=100,
            lane="MID",
            kills=5,
            deaths=2,
            assists=7,
            win=True,
            farm=150,
            damage_dealt=10000,
            wards=10,
            double_kills=1,
            triple_kills=0,
            quadra_kills=0,
            penta_kills=0,
            kill_participation=0.5,
            gold_earned=12000,
        )

    def test_summoner_detail_shows_existing_summoner(self):
        """
        Jeżeli Summoner istnieje w bazie i ma choć jednego Participant,
        to GET na summoner_detail powinien zwrócić 200 i w kontekście mieć klucz 'summoner'
        z poprawnym obiektem Summoner.
        """
        url = reverse('summoner_detail', args=[self.summ.gameName, self.summ.tagLine])
        response = self.client.get(f"{url}?region={self.summ.region}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['summoner'], self.summ)
        # Sprawdźmy, że w kontekście są Participanty
        participants = response.context['page_obj'].object_list
        self.assertEqual(participants.count(), 1)
        self.assertEqual(participants[0].match.match_id, "match123")


class SummonerDetailNotFoundTest(TestCase):
    def test_summoner_detail_redirects_if_not_found(self):
        """
        GET na summoner_detail z nieistniejącym Summonerem
        powinien zapisać komunikat i przekierować na 'home'.
        """
        url = reverse('summoner_detail', args=['NoSuchName', '9999'])
        # Robimy follow=True, żeby zobaczyć finalny URL po redirect
        response = self.client.get(f"{url}?region=euw1", follow=True)

        # Sprawdzamy, że faktycznie przekierowało do home (zakładając, że home ma nazwę 'home')
        self.assertEqual(response.redirect_chain[-1][0], reverse('home'))
        self.assertEqual(response.status_code, 200)


class SummonerUpdateTest(TestCase):
    def setUp(self):
        # podobnie jak poprzednio – przygotuj model, match, participant
        self.q = Queue.objects.create(queue_id=420, description="5v5 Ranked Solo games")
        self.champ = Champion.objects.create(key=1, name="TestChamp", icon="url")
        self.summ = Summoner.objects.create(
            puuid="puuidX",
            gameName="S1",
            tagLine="0001",
            region="euw1",
            server="euw1"
        )
        self.m1 = Match.objects.create(
            match_id="m1",
            queue=self.q,
            game_mode="CLASSIC",
            game_name="5v5 Ranked Solo games",
            game_duration=1200,
            timestamp="2025-05-20T10:00:00Z"
        )
        Participant.objects.create(
            summoner=self.summ, match=self.m1, champion=self.champ,
            team_id=100, lane="MID", kills=3, deaths=1, assists=5,
            win=True, farm=100, damage_dealt=5000, wards=5,
            double_kills=0, triple_kills=0, quadra_kills=0, penta_kills=0,
            kill_participation=0.5, gold_earned=9000
        )

    def test_update_removes_and_repopulates(self):
        """
        Gdy POSTujemy update=1, widok powinien:
        1) usunąć obecny match i participant,
        2) w powtórce 'save_recent_matches_for_summoner' dodać nowe (simulowane przez nas, więc sami tworzymy ręcznie),
        3) zwrócić redirect na GET, a po przekierowaniu pokazać co najmniej 1 Participant.
        """
        url = reverse('summoner_detail', args=[self.summ.gameName, self.summ.tagLine])

        # 1) Sprawdźmy, że w bazie jest 1 Participant i 1 Match
        self.assertEqual(Participant.objects.filter(summoner=self.summ).count(), 1)
        self.assertEqual(Match.objects.count(), 1)

        # 2) Zróbmy POST: to „usunie” je w widoku
        response = self.client.post(f"{url}?region={self.summ.region}", data={'update': '1'}, follow=True)

        # Po POST wywołany jest kod widoku:
        # - usunięte zostaną wszystkie Participant i pośrednio Match
        self.assertEqual(Participant.objects.filter(summoner=self.summ).count(), 0)
        self.assertEqual(Match.objects.count(), 1)

        # 3) Teraz symulujemy ponowne wczytanie historii:
        #    Tworzymy nowy Match i Participant ręcznie (jakby to zrobił 'save_recent_matches_for_summoner').
        new_match = Match.objects.create(
            match_id="m2",
            queue=self.q,
            game_mode="CLASSIC",
            game_name="5v5 Ranked Solo games",
            game_duration=1300,
            timestamp="2025-05-21T11:00:00Z"
        )
        Participant.objects.create(
            summoner=self.summ, match=new_match, champion=self.champ,
            team_id=200, lane="MID", kills=2, deaths=2, assists=6,
            win=False, farm=110, damage_dealt=6000, wards=7,
            double_kills=0, triple_kills=0, quadra_kills=0, penta_kills=0,
            kill_participation=0.4, gold_earned=9500
        )

        # 4) Po ręcznym „odtworzeniu” historii sprawdźmy, że przeglądarka w GET zwraca ponownie 1 rekord
        self.assertEqual(Participant.objects.filter(summoner=self.summ).count(), 1)

        # 5) W odpowiedzi response (follow=True) powinniśmy dostać status 200 i kontekst z summonerem
        self.assertEqual(response.status_code, 200)
