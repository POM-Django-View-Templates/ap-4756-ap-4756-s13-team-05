from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Book
from author.models import Author
from authentication.models import CustomUser, ROLE_LIBRARIAN
from order.models import Order


def _filter_books(query: str, author_id: str):
    """Filter book queryset by search query and/or author ID."""
    books = Book.objects.prefetch_related('authors').all()

    if query:
        books = books.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if author_id and author_id.isdigit():
        books = books.filter(authors__id=int(author_id))

    return books.distinct().order_by('id')


def _validate_book_data(name: str, description: str, count: str) -> str | None:
    """Validate book fields for creation."""
    if not name:
        return 'Book name is required.'
    if len(name) > Book.NAME_MAX_LEN:
        return f'Book name cannot exceed {Book.NAME_MAX_LEN} characters.'
    if len(description) > Book.DESCRIPTION_MAX_LEN:
        return f'Description cannot exceed {Book.DESCRIPTION_MAX_LEN} characters.'
    if not count.isdigit() or int(count) < 0:
        return 'Count must be a positive integer.'
    return None


def _create_book(name: str, description: str, count: str, selected_authors_ids: list[str]) -> Book:
    """Create book instance and attach selected authors."""
    book = Book(name=name, description=description, count=int(count))
    book.save()
    if selected_authors_ids:
        selected_authors = Author.objects.filter(id__in=selected_authors_ids)
        book.authors.set(selected_authors)
    return book


def book_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')

    query = request.GET.get('q', '').strip()
    author_id = request.GET.get('author_id', '').strip()

    books = _filter_books(query, author_id)
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

        error = _validate_book_data(name, description, count)
        if not error:
            book = _create_book(name, description, count, selected_authors_ids)
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
