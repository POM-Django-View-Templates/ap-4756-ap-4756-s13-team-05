from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

from .models import CustomUser

# Create your views here.
def index(request):
    return render(request, 'authentication/index.html')

def register(request):
    if request.method == "GET":
        return render(request, "authentication/register.html")

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")
    role_raw = request.POST.get("role", "0")

    error = None

    if not email or not password:
        error = "Email and password are required."
    elif password != confirm_password:
        error = "Passwords do not match."
    elif CustomUser.objects.filter(email=email).exists():
        error = "User with this email already exists."

    try:
        role = int(role_raw)
        if role not in (0, 1):
            role = 0
    except ValueError:
        role = 0

    if error:
        return render(
            request,
            "authentication/register.html",
            {
                "error": error,
                "form_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "middle_name": middle_name,
                    "email": email,
                    "role": role,
                },
            },
        )

    user = CustomUser.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        role=role,
        is_active=True,  # important: otherwise login may fail
    )

    auth_login(request, user)
    return redirect("home")

def login(request):
    if request.method == "GET":
        return render(request, "authentication/login.html")

    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")

    # For Django auth backends, pass username=... even with custom USERNAME_FIELD
    user = authenticate(request, username=email, password=password)

    if user is None:
        return render(
            request,
            "authentication/login.html",
            {"error": "Invalid email or password.", "email": email},
        )

    auth_login(request, user)
    return redirect("home")

def user_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != 1:
        return redirect('home')
    users = CustomUser.objects.all().order_by('id')
    return render(request, 'authentication/user_list.html', {'users': users})
    
def user_detail(request: HttpRequest, user_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    # Role control
    if request.user.role != 1 and request.user.id != user_id:
        return redirect('home')
    target_user = get_object_or_404(CustomUser, pk=user_id)
    return render(request, 'authentication/user_detail.html', {'target_user': target_user})

def logout(request):
    auth_logout(request)
    return redirect("login")