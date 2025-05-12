from django.contrib import admin
from .models import User, Company

admin.site.register(User)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'created_at']
