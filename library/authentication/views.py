from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

from .models import CustomUser, ROLE_VISITOR, ROLE_LIBRARIAN

# Create your views here.
def index(request):
    return render(request, 'authentication/index.html')

def register(request):
    context = {
        "role_visitor": ROLE_VISITOR,
        "role_librarian": ROLE_LIBRARIAN,
        "first_name_max_len": CustomUser.FIRST_NAME_MAX_LEN,
        "last_name_max_len": CustomUser.LAST_NAME_MAX_LEN,
        "middle_name_max_len": CustomUser.MIDDLE_NAME_MAX_LEN,
        "email_max_len": CustomUser.EMAIL_MAX_LEN,
    }

    if request.method == "GET":
        return render(request, "authentication/register.html", context)

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")
    role_raw = request.POST.get("role", str(ROLE_VISITOR))

    error = None

    if not email or not password:
        error = "Email and password are required."
    elif password != confirm_password:
        error = "Passwords do not match."
    elif CustomUser.objects.filter(email=email).exists():
        error = "User with this email already exists."

    try:
        role = int(role_raw)
        if role not in (ROLE_VISITOR, ROLE_LIBRARIAN):
            role = ROLE_VISITOR
    except ValueError:
        role = ROLE_VISITOR

    if error:
        context.update({
            "error": error,
            "form_data": {
                "first_name": first_name,
                "last_name": last_name,
                "middle_name": middle_name,
                "email": email,
                "role": role,
            },
        })
        return render(request, "authentication/register.html", context)

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
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')
    users = CustomUser.objects.all().order_by('id')
    return render(request, 'authentication/user_list.html', {'users': users})
    
def user_detail(request: HttpRequest, user_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    # Role control
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN and request.user.id != user_id:
        return redirect('home')
    target_user = get_object_or_404(CustomUser, pk=user_id)
    return render(request, 'authentication/user_detail.html', {'target_user': target_user})

def logout(request):
    auth_logout(request)
    return redirect("login")