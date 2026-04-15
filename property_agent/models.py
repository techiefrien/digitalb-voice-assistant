from django.db import models


class Property(models.Model):

    PROPERTY_TYPE_CHOICES = [
        ('1BHK', '1 BHK'),
        ('2BHK', '2 BHK'),
        ('3BHK', '3 BHK'),
        ('4BHK', '4 BHK'),
        ('Villa', 'Villa'),
        ('Plot', 'Plot'),
    ]

    FURNISHING_CHOICES = [
        ('unfurnished',      'Unfurnished'),
        ('semi_furnished',   'Semi Furnished'),
        ('fully_furnished',  'Fully Furnished'),
    ]

    # ── Core details ──────────────────────────────────────
    name          = models.CharField(max_length=255)
    location      = models.CharField(max_length=255)
    city          = models.CharField(max_length=100)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    description   = models.TextField(blank=True, null=True)

    # ── Pricing ───────────────────────────────────────────
    price         = models.DecimalField(max_digits=12, decimal_places=2)

    # ── Size & structure ──────────────────────────────────
    carpet_area   = models.PositiveIntegerField(help_text="Area in square feet")
    bedrooms      = models.PositiveIntegerField()
    bathrooms     = models.PositiveIntegerField()
    floor_number  = models.PositiveIntegerField(blank=True, null=True)
    total_floors  = models.PositiveIntegerField(blank=True, null=True)

    # ── Amenities ─────────────────────────────────────────
    amenities     = models.TextField(
                        blank=True, null=True,
                        help_text="Comma separated: Gym, Pool, Parking, etc."
                    )
    furnishing    = models.CharField(
                        max_length=20,
                        choices=FURNISHING_CHOICES,
                        default='unfurnished'
                    )
    parking       = models.BooleanField(default=False)

    # ── Status ────────────────────────────────────────────
    is_active     = models.BooleanField(default=True)

    # ── Timestamps ────────────────────────────────────────
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering        = ['-created_at']
        verbose_name    = 'Property'
        verbose_name_plural = 'Properties'

    def __str__(self):
        return f"{self.name} — {self.location} ({self.property_type})"

    @property
    def price_in_lakhs(self):
        return round(self.price / 100000, 2)


    def amenities_list(self):
        if self.amenities:
            return [a.strip() for a in self.amenities.split(',')]
        return []


class Transcript(models.Model):

    property      = models.ForeignKey(
                        Property,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='transcripts'
                    )
    
    caller_query  = models.TextField()
    ai_response   = models.TextField()
    timestamp     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Call at {self.timestamp:%d %b %Y %H:%M} — {self.caller_query[:50]}"
    

