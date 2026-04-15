from django.shortcuts import render , redirect
from django.contrib.auth import login , authenticate
from django.contrib import messages
from django.contrib.auth.models import User
# Create your views here.

def sign_in(request):
    if request.user.is_authenticated:
        return redirect('property_list')
    
    if request.method == 'POST':
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()

        user = authenticate(request , username=username , password=password)
        
        if user is None:
            messages.error(request , 'Invalid username or password')
            return redirect(request.path_info)
        
        login(request , user)
        messages.success(request , "Logged in successfully")
        return redirect('property_list')
    
    return render(request , 'accounts/sign-in.html')


