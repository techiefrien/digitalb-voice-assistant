from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from rest_framework.viewsets import ModelViewSet
from django.db.models import Avg, Count
from .models import Property
from .serializers import PropertySerialzer


def home(request):
    return render(request , 'property_agent/home.html')

@login_required
def property_list(request):
    properties = Property.objects.all().order_by('-created_at')

    # search
    q = request.GET.get('q')
    if q:
        properties = properties.filter(name__icontains=q) | \
                     properties.filter(location__icontains=q)

    # filters
    ptype = request.GET.get('type')
    if ptype:
        properties = properties.filter(property_type=ptype)

    city = request.GET.get('city')
    if city:
        properties = properties.filter(location__icontains=city)

    # stats
    total_count  = Property.objects.count()
    active_count = Property.objects.filter(is_active=True).count()
    avg_price    = Property.objects.aggregate(a=Avg('price'))['a'] or 0
    avg_price    = f"{int(avg_price):,}"
    city_count   = Property.objects.values('location').distinct().count()
    cities       = Property.objects.values_list('location', flat=True).distinct()

    # pagination
    paginator   = Paginator(properties, 8)
    page_number = request.GET.get('page')
    properties  = paginator.get_page(page_number)

    return render(request, 'property_agent/property_list.html', {
        'properties':   properties,
        'total_count':  total_count,
        'active_count': active_count,
        'avg_price':    avg_price,
        'city_count':   city_count,
        'cities':       cities,
    })


# ── Property Detail ───────────────────────────────────────────────────────────
@login_required
def property_detail(request, pk):
    property = get_object_or_404(Property, pk=pk)
    transcripts = property.transcripts.all().order_by('-timestamp')[:10]

    return render(request, 'property_agent/property_detail.html', {
        'property':   property,
        'transcripts': transcripts,
    })



# ── Add Property ──────────────────────────────────────────────────────────────
@login_required
def property_add(request):
    if request.method == 'POST':
        try:
            Property.objects.create(
                name          = request.POST.get('name'),
                location      = request.POST.get('location'),
                city          = request.POST.get('city'),
                property_type = request.POST.get('property_type'),
                description   = request.POST.get('description', ''),
                price         = request.POST.get('price'),
                carpet_area   = request.POST.get('carpet_area'),
                bedrooms      = request.POST.get('bedrooms'),
                bathrooms     = request.POST.get('bathrooms'),
                floor_number  = request.POST.get('floor_number') or None,
                total_floors  = request.POST.get('total_floors') or None,
                amenities     = request.POST.get('amenities', ''),
                furnishing    = request.POST.get('furnishing'),
                parking       = request.POST.get('parking') == 'on',
                is_active     = request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'Property added successfully.')
            return redirect('property_list')

        except Exception as e:
            messages.error(request, f'Error adding property: {str(e)}')

    return render(request, 'property_agent/property_add.html', {
        'property_types': Property.PROPERTY_TYPE_CHOICES,
        'furnishing_types': Property.FURNISHING_CHOICES,
    })

# ── Edit Property ─────────────────────────────────────────────────────────────
@login_required
def property_edit(request, pk):
    property = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':
        try:
            property.name          = request.POST.get('name')
            property.location      = request.POST.get('location')
            property.city          = request.POST.get('city')
            property.property_type = request.POST.get('property_type')
            property.description   = request.POST.get('description', '')
            property.price         = request.POST.get('price')
            property.carpet_area   = request.POST.get('carpet_area')
            property.bedrooms      = request.POST.get('bedrooms')
            property.bathrooms     = request.POST.get('bathrooms')
            property.floor_number  = request.POST.get('floor_number') or None
            property.total_floors  = request.POST.get('total_floors') or None
            property.amenities     = request.POST.get('amenities', '')
            property.furnishing    = request.POST.get('furnishing')
            property.parking       = request.POST.get('parking') == 'on'
            property.is_active     = request.POST.get('is_active') == 'on'
            property.save()

            messages.success(request, 'Property updated successfully.')
            return redirect('property_list')

        except Exception as e:
            messages.error(request, f'Error updating property: {str(e)}')

    return render(request, 'property_agent/property_edit.html', {
        'property':        property,
        'property_types':  Property.PROPERTY_TYPE_CHOICES,
        'furnishing_types': Property.FURNISHING_CHOICES,
    })


# ── Delete Property ───────────────────────────────────────────────────────────
@login_required
def property_delete(request, pk):
    property = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':
        property_name = property.name
        property.delete()
        messages.success(request, f'"{property_name}" deleted successfully.')
        return redirect('property_list')

    # GET request — show confirmation page
    return render(request, 'property_agent/property_confirm_delete.html', {
        'property': property,
    })




#API for front-end integration 
class PropertyViewSet(ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerialzer