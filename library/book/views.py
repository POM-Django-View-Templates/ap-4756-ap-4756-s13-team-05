from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Book
from author.models import Author
from authentication.models import CustomUser, ROLE_LIBRARIAN
from order.models import Order


def book_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    query = request.GET.get('q', '').strip()
    author_id = request.GET.get('author_id', '').strip()

    books = Book.objects.prefetch_related('authors').all()

    # Filter by name and description
    if query:
        books = books.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # Filter by author
    if author_id and author_id.isdigit():
        books = books.filter(authors__id=int(author_id))

    books = books.distinct().order_by('id')
    authors = Author.objects.all().order_by('surname', 'name')

    return render(request, 'book/book_list.html', {
        'books': books,
        'authors': authors,
        'query': query,
        'selected_author_id': int(author_id) if author_id.isdigit() else '',
    })


def book_detail(request: HttpRequest, book_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    book = get_object_or_404(Book.objects.prefetch_related('authors'), pk=book_id)
    return render(request, 'book/book_detail.html', {'book': book})


def book_create(request: HttpRequest) -> HttpResponse:
    # Only for librarian
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    authors = Author.objects.all().order_by('surname', 'name')
    error = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        count = request.POST.get('count', str(Book.DEFAULT_COUNT)).strip()
        selected_authors_ids = request.POST.getlist('authors')

        if not name:
            error = 'Book name is required.'
        elif len(name) > Book.NAME_MAX_LEN:
            error = f'Book name cannot exceed {Book.NAME_MAX_LEN} characters.'
        elif len(description) > Book.DESCRIPTION_MAX_LEN:
            error = f'Description cannot exceed {Book.DESCRIPTION_MAX_LEN} characters.'
        elif not count.isdigit() or int(count) < 0:
            error = 'Count must be a positive integer.'
        else:
            book = Book(name=name, description=description, count=int(count))
            book.save()
            if selected_authors_ids:
                selected_authors = Author.objects.filter(id__in=selected_authors_ids)
                book.authors.set(selected_authors)

            messages.success(request, f'Book "{book.name}" created successfully.')
            return redirect('book_list')

    return render(request, 'book/book_create.html', {
        'authors': authors,
        'error': error,
        'form_data': request.POST if request.method == 'POST' else {},
        'name_max_len': Book.NAME_MAX_LEN,
        'desc_max_len': Book.DESCRIPTION_MAX_LEN,
        'default_count': Book.DEFAULT_COUNT,
    })


def books_by_user(request: HttpRequest, user_id: int) -> HttpResponse:
    # Only for librarian
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    target_user = get_object_or_404(CustomUser, pk=user_id)

    active_orders = Order.objects.filter(user=target_user, end_at__isnull=True).select_related('book')

    return render(request, 'book/books_by_user.html', {
        'target_user': target_user,
        'active_orders': active_orders,
    })
