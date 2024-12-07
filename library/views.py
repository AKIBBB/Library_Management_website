from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm, LoginForm, EditProfileForm
from django.contrib import messages
from .models import Book, BorrowingHistory, Review, UserProfile, Category
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from decimal import Decimal,InvalidOperation
from django.utils.timezone import now
from datetime import datetime


def home(request):
    books = Book.objects.all()
    categories = Category.objects.all()  
    selected_book_id = request.session.get('selected_book_id', None)
    selected_category = request.GET.get('category', None)
    query = request.GET.get('q', '')

    if query:
        books = books.filter(title__icontains=query) 
    if selected_category:
        books = books.filter(category__id=selected_category)  

    purchased_books = []
    if request.user.is_authenticated:
        purchased_books = BorrowingHistory.objects.filter(user=request.user).values_list('book_id', flat=True)

    if request.method == "POST":
        book_id = request.POST.get("book_id")
        action = request.POST.get("action")
        if action == "see_more":
            request.session['selected_book_id'] = book_id
            selected_book_id = book_id

    return render(request, 'library/home.html', {
        'books': books,
        'categories': categories,  
        'selected_category': selected_category,  
        'query': query, 
        'selected_book_id': selected_book_id,
        'purchased_books': purchased_books,  
    })



def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Registration successful!")
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'library/register.html', {'form': form})



def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'library/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('home')




@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    borrowing_history = BorrowingHistory.objects.filter(user=request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            form = EditProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Your profile has been updated successfully!")
                return redirect('profile')  
        elif 'deposit_money' in request.POST:
            amount = request.POST.get('amount')
            try:
                deposit_amount = Decimal(amount)
                if deposit_amount > 0:
                    user_profile.balance += deposit_amount
                    user_profile.save()
                    messages.success(request, f"${deposit_amount} has been added to your balance!")
                else:
                    messages.error(request, "Deposit amount must be greater than zero.")
            except (ValueError, InvalidOperation):
                messages.error(request, "Invalid deposit amount. Please enter a valid number.")
            return redirect('profile')  


    form = EditProfileForm(instance=request.user)
    return render(request, 'library/profile.html', {
        'form': form,
        'borrowing_history': borrowing_history,
        'user_profile': user_profile,  
    })

    



@login_required
def deposit_money(request):
    if request.method == 'POST':
        deposit_amount = request.POST.get('amount')
        if deposit_amount and deposit_amount.isdigit():
            deposit_amount = float(deposit_amount)
            profile = UserProfile.objects.get(user=request.user)
            profile.balance += deposit_amount  
            profile.save()
            messages.success(request, f'You have successfully deposited {deposit_amount}!')
        else:
            messages.error(request, 'Please enter a valid amount.')
    return render(request, 'library/deposit.html') 


def book_list(request):
    categories = Category.objects.all()
    books = Book.objects.all()
    category_filter = request.GET.get('category')
    if category_filter:
        books = books.filter(category__id=category_filter)

    return render(request, 'library/book_list.html', {
        'categories': categories,
        'books': books,
    })




@login_required
def borrow_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        return_date = request.POST.get('return_date')

        if not name or not email or not return_date:
            messages.error(request, "Please fill in all fields.")
        elif book.quantity > 0 and user_profile.balance >= book.price:
            user_profile.balance -= book.price
            user_profile.save()

            book.quantity -= 1
            book.save()
            BorrowingHistory.objects.create(
                user=request.user,
                book=book,
                name=name,
                email=email,
                return_date=return_date,
                borrow_date=now(),
            )

            messages.success(request, f'You have successfully borrowed "{book.title}".')
            return redirect('profile')
        elif book.quantity == 0:
            messages.error(request, f'"{book.title}" is out of stock.')
        else:
            messages.error(request, f'Insufficient balance to borrow "{book.title}".')

    return render(request, 'library/borrow_book.html', {'book': book})



@login_required
def return_book(request, history_id):
    history = get_object_or_404(BorrowingHistory, id=history_id, user=request.user)

    if not history.return_date:
        user_profile = request.user.userprofile
        user_profile.balance += history.book.price  
        user_profile.save()

        history.book.quantity += 1
        history.book.save()

        history.return_date = now()
        history.save()

        messages.success(request, f'You have successfully returned "{history.book.title}". Refund credited to your account.')
    else:
        messages.error(request, f'"{history.book.title}" has already been returned.')

    return redirect('profile')

@login_required
def buy_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if book.quantity > 0 and user_profile.balance >= book.price:
        user_profile.balance -= book.price
        user_profile.save()

        book.quantity -= 1
        book.save()

        send_mail(
            subject='Book Purchase Confirmation',
            message=f'Dear {request.user.username},\n\nYou have successfully purchased "{book.title}" for ${book.price}.\n\nThank you for your purchase!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
        )

        messages.success(request, f'You have successfully purchased "{book.title}". A confirmation email has been sent to you.')
    elif book.quantity == 0:
        messages.error(request, f'"{book.title}" is out of stock.')
    else:
        messages.error(request, f'Insufficient balance to buy "{book.title}".')

    return redirect('home')



@login_required
def review_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    user_purchased_books = BorrowingHistory.objects.filter(user=request.user, book=book).exists()
    if not user_purchased_books:
        messages.error(request, 'You can only review books you have purchased or borrowed.')
        return redirect(reverse('book_details', kwargs={'id': book.id}))
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Review.objects.create(user=request.user, book=book, content=content)
            messages.success(request, f'Your review for "{book.title}" has been posted.')
        else:
            messages.error(request, 'Review content cannot be empty.')

    return redirect(reverse('book_details', kwargs={'id': book.id}))


def book_details(request, id):
    book = get_object_or_404(Book, id=id)
    reviews = Review.objects.filter(book=book)
    return render(request, 'library/book_details.html', {'book': book, 'reviews': reviews})
