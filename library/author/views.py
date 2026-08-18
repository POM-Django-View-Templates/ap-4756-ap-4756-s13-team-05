from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from authentication.models import ROLE_LIBRARIAN
from .models import Author


def _validate_author_data(name: str, surname: str, patronymic: str) -> str | None:
    """Validate author fields presence and length limits."""
    if not name or not surname or not patronymic:
        return "All fields (Name, Surname, Middle name) are required."
    if (
        len(name) > Author.NAME_MAX_LEN
        or len(surname) > Author.SURNAME_MAX_LEN
        or len(patronymic) > Author.PATRONYMIC_MAX_LEN
    ):
        return f"Field length cannot exceed {Author.NAME_MAX_LEN} characters."
    return None


def _delete_author(request: HttpRequest, author_id: int) -> None:
    """Attempt to delete an author if not attached to any books."""
    author = Author.get_by_id(author_id)
    if not author:
        messages.error(request, "Author not found.")
        return

    if author.books.exists():
        messages.error(
            request,
            f'Cannot delete author "{author.name} {author.surname}" because they are attached to one or more books.',
        )
    else:
        Author.delete_by_id(author_id)
        messages.success(request, f'Author "{author.name} {author.surname}" was successfully deleted.')


def author_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    authors = Author.objects.prefetch_related('books').all().order_by('id')
    return render(request, 'author/author_list.html', {'authors': authors})


def author_create(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        surname = request.POST.get('surname', '').strip()
        patronymic = request.POST.get('patronymic', '').strip()

        error = _validate_author_data(name, surname, patronymic)
        if not error:
            Author.create(name=name, surname=surname, patronymic=patronymic)
            return redirect('author_list')

    return render(request, 'author/author_create.html', {
        'error': error,
        'form_data': request.POST if request.method == 'POST' else {},
        'name_max_len': Author.NAME_MAX_LEN,
        'surname_max_len': Author.SURNAME_MAX_LEN,
        'patronymic_max_len': Author.PATRONYMIC_MAX_LEN,
    })


def author_delete(request: HttpRequest, author_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != ROLE_LIBRARIAN:
        return redirect('home')

    if request.method == 'POST':
        _delete_author(request, author_id)

    return redirect('author_list')
