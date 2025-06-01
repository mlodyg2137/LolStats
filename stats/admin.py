from django.contrib import admin
from .models import Summoner, Match, Participant, Champion, Queue

@admin.register(Summoner)
class SummonerAdmin(admin.ModelAdmin):
    list_display = ('gameName', 'tagLine', 'region', 'date_added')
    search_fields = ('gameName', 'tagLine', 'region')

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('match_id', 'game_mode', 'timestamp', 'game_duration')
    search_fields = ('match_id',)

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('summoner', 'match', 'champion', 'kills', 'deaths', 'assists', 'win')
    search_fields = ('summoner__name', 'match__match_id')

admin.site.register(Champion)
admin.site.register(Queue)