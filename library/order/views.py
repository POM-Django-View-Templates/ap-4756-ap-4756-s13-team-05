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


def order_my(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    orders = Order.objects.filter(user=request.user).select_related('book').order_by('-created_at')
    return render(request, 'order/order_my.html', {'orders': orders})


def order_all(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    # For librarian only
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    orders = Order.objects.select_related('user', 'book').all().order_by('-created_at')
    return render(request, 'order/order_all.html', {'orders': orders})


def order_create(request: HttpRequest, book_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    book = get_object_or_404(Book, pk=book_id)

    # Check available copies
    if book.available_count <= 0:
        messages.error(request, f'Sorry, all copies of "{book.name}" are currently borrowed.')
        return redirect('book_detail', book_id=book.id)

    # Check if user already has an active order for this book
    already_borrowed = Order.objects.filter(user=request.user, book=book, end_at__isnull=True).exists()
    if already_borrowed:
        messages.error(request, f'You already have an active order for "{book.name}".')
        return redirect('book_detail', book_id=book.id)

    if request.method == 'POST':
        days = request.POST.get('days', str(DEFAULT_BORROW_DAYS))
        try:
            days_count = int(days)
            if days_count < MIN_BORROW_DAYS or days_count > MAX_BORROW_DAYS:
                days_count = DEFAULT_BORROW_DAYS
        except ValueError:
            days_count = DEFAULT_BORROW_DAYS

        plated_end_at = timezone.now() + datetime.timedelta(days=days_count)

        order = Order.create(user=request.user, book=book, plated_end_at=plated_end_at)
        if order:
            messages.success(request, f'Order for "{book.name}" created successfully!')
            return redirect('order_my')
        else:
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
        order = get_object_or_404(Order, pk=order_id)
        if order.end_at is None:
            order.end_at = timezone.now()
            order.save()
            messages.success(request, f'Order #{order.id} closed (Book returned).')
        else:
            messages.info(request, f'Order #{order.id} was already closed.')

    return redirect('order_all')
