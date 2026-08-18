import datetime
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from authentication.models import ROLE_LIBRARIAN
from .models import Order
from book.models import Book

DEFAULT_BORROW_DAYS = 14
MIN_BORROW_DAYS = 1
MAX_BORROW_DAYS = 30


def _check_borrow_eligibility(request: HttpRequest, book: Book) -> bool:
    """Verify if user can borrow the book (copies in stock and no active duplicate order)."""
    if book.available_count <= 0:
        messages.error(request, f'Sorry, all copies of "{book.name}" are currently borrowed.')
        return False

    already_borrowed = Order.objects.filter(user=request.user, book=book, end_at__isnull=True).exists()
    if already_borrowed:
        messages.error(request, f'You already have an active order for "{book.name}".')
        return False

    return True


def _parse_loan_days(days_raw: str | None) -> int:
    """Parse loan duration input within allowed minimum and maximum constraints."""
    if not days_raw:
        return DEFAULT_BORROW_DAYS
    try:
        days_count = int(days_raw)
        if MIN_BORROW_DAYS <= days_count <= MAX_BORROW_DAYS:
            return days_count
        return DEFAULT_BORROW_DAYS
    except (ValueError, TypeError):
        return DEFAULT_BORROW_DAYS


def _close_order(request: HttpRequest, order_id: int) -> None:
    """Close active order by recording end_at timestamp."""
    order = get_object_or_404(Order, pk=order_id)
    if order.end_at is None:
        order.end_at = timezone.now()
        order.save()
        messages.success(request, f'Order #{order.id} closed (Book returned).')
    else:
        messages.info(request, f'Order #{order.id} was already closed.')


def order_my(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    orders = Order.objects.filter(user=request.user).select_related('book').order_by('-created_at')
    return render(request, 'order/order_my.html', {'orders': orders})


def order_all(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    orders = Order.objects.select_related('user', 'book').all().order_by('-created_at')
    return render(request, 'order/order_all.html', {'orders': orders})


def order_create(request: HttpRequest, book_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    book = get_object_or_404(Book, pk=book_id)
    if not _check_borrow_eligibility(request, book):
        return redirect('book_detail', book_id=book.id)

    if request.method == 'POST':
        days_count = _parse_loan_days(request.POST.get('days'))
        plated_end_at = timezone.now() + datetime.timedelta(days=days_count)

        order = Order.create(user=request.user, book=book, plated_end_at=plated_end_at)
        if order:
            messages.success(request, f'Order for "{book.name}" created successfully!')
            return redirect('order_my')
        messages.error(request, 'Could not create order. Please try again.')

    return render(request, 'order/order_create.html', {
        'book': book,
        'default_date': (timezone.now() + datetime.timedelta(days=DEFAULT_BORROW_DAYS)).strftime('%Y-%m-%d'),
        'default_days': DEFAULT_BORROW_DAYS,
        'min_days': MIN_BORROW_DAYS,
        'max_days': MAX_BORROW_DAYS,
    })


def order_close(request: HttpRequest, order_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    if request.method == 'POST':
        _close_order(request, order_id)

    return redirect('order_all')
