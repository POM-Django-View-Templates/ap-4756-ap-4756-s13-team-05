from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from authentication.models import ROLE_LIBRARIAN
from .models import Author


def author_list(request: HttpRequest) -> HttpResponse:
    # Check role
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

        # Validation
        if not name or not surname or not patronymic:
            error = 'All fields (Name, Surname, Middle name) are required.'
        elif (
            len(name) > Author.NAME_MAX_LEN
            or len(surname) > Author.SURNAME_MAX_LEN
            or len(patronymic) > Author.PATRONYMIC_MAX_LEN
        ):
            error = f'Field length cannot exceed {Author.NAME_MAX_LEN} characters.'
        else:
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
        author = Author.get_by_id(author_id)
        if not author:
            messages.error(request, 'Author not found.')
            return redirect('author_list')

        # Delete if don't have books
        if author.books.exists():
            messages.error(request, f'Cannot delete author "{author.name} {author.surname}" because they are attached to one or more books.')
        else:
            Author.delete_by_id(author_id)
            messages.success(request, f'Author "{author.name} {author.surname}" was successfully deleted.')

    return redirect('author_list')
