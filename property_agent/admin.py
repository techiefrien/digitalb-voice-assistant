from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Property, Transcript


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display  = ['name', 'location', 'city', 'property_type',
                     'price', 'carpet_area', 'is_active']
    list_filter   = ['property_type', 'city', 'is_active', 'furnishing']
    search_fields = ['name', 'location', 'city']
    list_editable = ['is_active']


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display  = ['property', 'caller_query', 'ai_response', 'timestamp']
    readonly_fields = ['timestamp']