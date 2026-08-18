from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Author


def author_list(request: HttpRequest) -> HttpResponse:
    # Check role
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != 1:
        return redirect('home')

    authors = Author.objects.prefetch_related('books').all().order_by('id')
    return render(request, 'author/author_list.html', {'authors': authors})


def author_create(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != 1:
        return redirect('home')

    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        surname = request.POST.get('surname', '').strip()
        patronymic = request.POST.get('patronymic', '').strip()

        # Validation
        if not name or not surname or not patronymic:
            error = 'All fields (Name, Surname, Middle name) are required.'
        elif len(name) > 20 or len(surname) > 20 or len(patronymic) > 20:
            error = 'Field length cannot exceed 20 characters.'
        else:
            Author.create(name=name, surname=surname, patronymic=patronymic)
            return redirect('author_list')

    return render(request, 'author/author_create.html', {
        'error': error,
        'form_data': request.POST if request.method == 'POST' else {}
    })


def author_delete(request: HttpRequest, author_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login')
    if getattr(request.user, 'role', None) != 1:
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
