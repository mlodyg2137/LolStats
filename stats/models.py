from django.db import models


class Queue(models.Model):
    queue_id = models.IntegerField(unique=True)
    description = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.description or 'brak opisu'}"


class Champion(models.Model):
    key = models.IntegerField(unique=True)
    name = models.CharField(max_length=15, unique=True)
    icon = models.CharField(max_length=120)

    def __str__(self):
        return f"{self.name}"


class Summoner(models.Model):
    puuid = models.CharField(max_length=100, unique=True)
    gameName = models.CharField(max_length=16)
    tagLine = models.CharField(max_length=6)
    region = models.CharField(max_length=10)
    server = models.CharField(max_length=4)
    date_added = models.DateTimeField(auto_now_add=True)

    summoner_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    summoner_level = models.PositiveIntegerField(null=True)
    icon = models.CharField(max_length=120, null=True, blank=True)

    rank_solo = models.CharField(max_length=13, null=True, blank=True)
    solo_wins = models.PositiveIntegerField(null=True)
    solo_loses = models.PositiveIntegerField(null=True)
    solo_kda = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    solo_main_role = models.CharField(max_length=7, null=True, blank=True)
    solo_vision_avg = models.FloatField(null=True)
    solo_gold_per_min = models.PositiveIntegerField(null=True)
    solo_minions_per_min = models.FloatField(null=True)

    rank_flex = models.CharField(max_length=13, null=True, blank=True)
    flex_wins = models.PositiveIntegerField(null=True)
    flex_loses = models.PositiveIntegerField(null=True)
    flex_kda = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    flex_main_role = models.CharField(max_length=7, null=True, blank=True)
    flex_vision_avg = models.FloatField(null=True)
    flex_gold_per_min = models.PositiveIntegerField(null=True)
    flex_minions_per_min = models.FloatField(null=True)

    def __str__(self):
        return f"{self.gameName}#{self.tagLine} ({self.server})"
    
    @property
    def solo_matches_num(self):
        return (self.solo_wins or 0) + (self.solo_loses or 0)

    @property
    def solo_winratio(self):
        return f"{(self.solo_wins / self.solo_matches_num)*100:.1f}%" if self.solo_matches_num > 0 else "0.0%"
    
    @property
    def flex_matches_num(self):
        return (self.flex_wins or 0) + (self.flex_loses or 0)
    
    @property
    def flex_winratio(self):
        return f"{(self.flex_wins / self.flex_matches_num)*100:.1f}%" if self.flex_matches_num > 0 else "0.0%"
    
    @property
    def rank_solo_formatted(self):
        if self.rank_solo is None:
            return None
        rank_type, rank_num = self.rank_solo.split()
        if rank_type == "CHALLENGER":
            return "Challenger"
        return f"{rank_type[0].upper()}{rank_type[1:].lower()} {rank_num}"
    
    @property
    def rank_flex_formatted(self):
        if self.rank_flex is None:
            return None
        rank_type, rank_num = self.rank_flex.split()
        if rank_type == "CHALLENGER":
            return "Challenger"
        return f"{rank_type[0].upper()}{rank_type[1:].lower()} {rank_num}"
    
    @property
    def solo_main_role_formatted(self):
        return f"{self.solo_main_role.capitalize()}" if self.solo_main_role else "Brak"
    
    @property
    def flex_main_role_formatted(self):
        return f"{self.flex_main_role.capitalize()}" if self.flex_main_role else "Brak"


class SummonerChampion(models.Model):
    summoner = models.ForeignKey(Summoner, on_delete=models.CASCADE)
    champion = models.ForeignKey(Champion, on_delete=models.CASCADE)
    matches_num = models.PositiveIntegerField()
    winratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    kda = models.DecimalField(max_digits=6, decimal_places=2, null=True)

    def __str__(self):
        return f"{self.champion.name} ({self.summoner.gameName}#{self.summoner.tagLine})"


class Match(models.Model):
    match_id = models.CharField(max_length=100, unique=True)
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, null=True)
    game_mode = models.CharField(max_length=20, null=True)
    game_name = models.CharField(max_length=20, null=True)
    game_duration = models.PositiveIntegerField(null=True)
    timestamp = models.DateTimeField(null=True)
    summoners = models.ManyToManyField(Summoner, through='Participant')

    team0_kills = models.PositiveIntegerField(null=True)
    team0_deaths = models.PositiveIntegerField(null=True)
    team0_assists = models.PositiveIntegerField(null=True)

    team1_kills = models.PositiveIntegerField(null=True)
    team1_deaths = models.PositiveIntegerField(null=True)
    team1_assists = models.PositiveIntegerField(null=True)

    def __str__(self):
        return f"Match {self.match_id} - {self.queue}"
    
    @property
    def duration_minutes(self):
        return self.game_duration // 60
    
    @property
    def duration_seconds(self):
        return self.game_duration % 60


class Participant(models.Model):
    summoner = models.ForeignKey(Summoner, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    team_id = models.IntegerField(null=True) # 100 - team 0, 200 - team 1
    champion = models.ForeignKey(Champion, on_delete=models.CASCADE)
    lane = models.CharField(max_length=7, null=True)
    kills = models.IntegerField(null=True)
    deaths = models.IntegerField(null=True)
    assists = models.IntegerField(null=True)
    win = models.BooleanField(null=True)
    kill_participation = models.FloatField(null=True)
    farm = models.PositiveIntegerField(null=True)
    wards = models.PositiveIntegerField(null=True)
    double_kills = models.SmallIntegerField(null=True)
    triple_kills = models.SmallIntegerField(null=True)
    quadra_kills = models.SmallIntegerField(null=True)
    penta_kills = models.SmallIntegerField(null=True)
    damage_dealt = models.PositiveIntegerField(null=True)
    gold_earned = models.PositiveBigIntegerField(null=True)

    def __str__(self):
        return f"{self.summoner.gameName} in {self.match.match_id}"
