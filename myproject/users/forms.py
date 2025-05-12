from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.contrib.auth.hashers import make_password

from .models import User, Company

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'role', 'company', 'companies']

class CustomUserChangeForm(UserChangeForm):
    new_password = forms.CharField(
        label='Новый пароль',
        required=False,
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ['username', 'role', 'company', 'companies']

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('new_password')
        if password:
            user.password = make_password(password)
        if commit:
            user.save()
            self.save_m2m()  # обязательно для сохранения ManyToMany

            # Сброс предыдущих компаний, где он мог быть tech_lead
            Company.objects.filter(tech_lead=user).exclude(id__in=user.companies.values_list('id', flat=True)).update(
                tech_lead=None)

            # Назначение техлидом во всех выбранных компаниях
            for company in user.companies.all():
                company.tech_lead = user
                company.save()

        return user

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'description', 'tech_lead']
        labels = {
            'name': 'Название предприятия',
            'address': 'Адрес',
            'description': 'Описание',
            'tech_lead': 'Технический руководитель',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание'}),
        }