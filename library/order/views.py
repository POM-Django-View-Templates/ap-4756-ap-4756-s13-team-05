import datetime
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Order
from book.models import Book


def order_my(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    orders = Order.objects.filter(user=request.user).select_related('book').order_by('-created_at')
    return render(request, 'order/order_my.html', {'orders': orders})


def order_all(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    # For librarian only
    if getattr(request.user, 'role', None) != 1:
        return redirect('home')

    orders = Order.objects.select_related('user', 'book').all().order_by('-created_at')
    return render(request, 'order/order_all.html', {'orders': orders})


def order_create(request: HttpRequest, book_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    book = get_object_or_404(Book, pk=book_id)

    # Check available copies
    active_orders_count = Order.objects.filter(book=book, end_at__isnull=True).count()
    if active_orders_count >= book.count:
        messages.error(request, f'Sorry, all copies of "{book.name}" are currently borrowed.')
        return redirect('book_detail', book_id=book.id)

    # Check if user already has an active order for this book
    already_borrowed = Order.objects.filter(user=request.user, book=book, end_at__isnull=True).exists()
    if already_borrowed:
        messages.error(request, f'You already have an active order for "{book.name}".')
        return redirect('book_detail', book_id=book.id)

    if request.method == 'POST':
        days = request.POST.get('days', '14')
        try:
            days_count = int(days)
            if days_count < 1 or days_count > 30:
                days_count = 14
        except ValueError:
            days_count = 14

        plated_end_at = timezone.now() + datetime.timedelta(days=days_count)

        order = Order.create(user=request.user, book=book, plated_end_at=plated_end_at)
        if order:
            messages.success(request, f'Order for "{book.name}" created successfully!')
            return redirect('order_my')
        else:
            messages.error(request, 'Could not create order. Please try again.')

    return render(request, 'order/order_create.html', {
        'book': book,
        'default_date': (timezone.now() + datetime.timedelta(days=14)).strftime('%Y-%m-%d'),
    })


def order_close(request: HttpRequest, order_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != 1:
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
