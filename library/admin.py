from django.contrib import admin
from .models import Book, Category, BorrowingHistory, Review

# Register your models here.
admin.site.register(Book)
admin.site.register(Category)
admin.site.register(BorrowingHistory)
admin.site.register(Review)
