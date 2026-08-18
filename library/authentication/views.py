from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

from .models import CustomUser, ROLE_VISITOR, ROLE_LIBRARIAN

# Create your views here.
def index(request):
    return render(request, 'authentication/index.html')

def _get_register_context() -> dict:
    """Return default context for the registration page."""
    return {
        "role_visitor": ROLE_VISITOR,
        "role_librarian": ROLE_LIBRARIAN,
        "first_name_max_len": CustomUser.FIRST_NAME_MAX_LEN,
        "last_name_max_len": CustomUser.LAST_NAME_MAX_LEN,
        "middle_name_max_len": CustomUser.MIDDLE_NAME_MAX_LEN,
        "email_max_len": CustomUser.EMAIL_MAX_LEN,
    }


def _parse_role(role_raw: str) -> int:
    """Parse and validate user role integer, defaulting to visitor."""
    try:
        role = int(role_raw)
        return role if role in (ROLE_VISITOR, ROLE_LIBRARIAN) else ROLE_VISITOR
    except (ValueError, TypeError):
        return ROLE_VISITOR


def _extract_register_data(post_data) -> dict:
    """Extract and sanitize form input from registration POST request."""
    return {
        "first_name": post_data.get("first_name", "").strip(),
        "last_name": post_data.get("last_name", "").strip(),
        "middle_name": post_data.get("middle_name", "").strip(),
        "email": post_data.get("email", "").strip().lower(),
        "password": post_data.get("password", ""),
        "confirm_password": post_data.get("confirm_password", ""),
        "role": _parse_role(post_data.get("role", str(ROLE_VISITOR))),
    }


def _validate_register_data(form_data: dict) -> str | None:
    """Validate registration credentials and uniqueness."""
    if not form_data["email"] or not form_data["password"]:
        return "Email and password are required."
    if form_data["password"] != form_data["confirm_password"]:
        return "Passwords do not match."
    if CustomUser.objects.filter(email=form_data["email"]).exists():
        return "User with this email already exists."
    return None


def register(request: HttpRequest) -> HttpResponse:
    context = _get_register_context()
    if request.method == "GET":
        return render(request, "authentication/register.html", context)

    form_data = _extract_register_data(request.POST)
    error = _validate_register_data(form_data)

    if error:
        context.update({"error": error, "form_data": form_data})
        return render(request, "authentication/register.html", context)

    user = CustomUser.objects.create_user(
        email=form_data["email"],
        password=form_data["password"],
        first_name=form_data["first_name"],
        last_name=form_data["last_name"],
        middle_name=form_data["middle_name"],
        role=form_data["role"],
        is_active=True,
    )

    auth_login(request, user)
    return redirect("home")


def login(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, "authentication/login.html")

    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")

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