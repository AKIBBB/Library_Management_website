from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('books/', views.book_list, name='book_list'),
    path('return/<int:history_id>/', views.return_book, name='return_book'),
    path('review/<int:book_id>/', views.review_book, name='review_book'),
    path('deposit/', views.deposit_money, name='deposit_money'),
    path('buy/<int:book_id>/', views.buy_book, name='buy_book'),
    path('borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    path('book/<int:id>/', views.book_details, name='book_details'),
    path('review/<int:book_id>/', views.review_book, name='review_book'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)