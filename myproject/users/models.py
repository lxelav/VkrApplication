from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('tech_lead', 'Технический руководитель'),
        ('methodist', 'Методист'),
        ('expert', 'Эксперт'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='expert')

    company = models.ForeignKey('Company', on_delete=models.SET_NULL, related_name='users', null=True, blank=True)
    companies = models.ManyToManyField('Company', related_name='leads', blank=True)

    def get_company_display(self):
        if self.role == 'tech_lead':
            return ", ".join([c.name for c in self.companies.all()])
        return self.company.name if self.company else "—"


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    tech_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'tech_lead'},  # фильтруем по роли
        related_name='supervised_companies'
    )

    def __str__(self):
        return self.name


class JobTitle(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='job_titles')


class Checklist(models.Model):
    title = models.CharField(max_length=255)
    company = models.ForeignKey('Company', on_delete=models.CASCADE)  # <-- добавлено
    job_title = models.ForeignKey('JobTitle', on_delete=models.CASCADE)
    data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)


class CompetencyMatrix(models.Model):
    job_title = models.ForeignKey(JobTitle, on_delete=models.CASCADE, related_name='competency_matrices')
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Матрица {self.job_title.name} от {self.created_at.strftime('%d.%m.%Y')}"


class Competency(models.Model):
    name = models.CharField(max_length=255)
    matrix = models.ForeignKey(CompetencyMatrix, on_delete=models.CASCADE, related_name='competencies')


class ProcessGroup(models.Model):
    name = models.CharField(max_length=255)
    matrix = models.ForeignKey(CompetencyMatrix, on_delete=models.CASCADE, related_name='groups')

    def __str__(self):
        return self.name


class ProcessSubGroup(models.Model):
    name = models.CharField(max_length=255)
    group = models.ForeignKey(ProcessGroup, on_delete=models.CASCADE, related_name='subgroups')


class Process(models.Model):
    name = models.CharField(max_length=255)
    matrix = models.ForeignKey(CompetencyMatrix, on_delete=models.CASCADE)
    subgroup = models.ForeignKey(ProcessSubGroup, on_delete=models.CASCADE, related_name='processes')


class Criterion(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='criteria')
    text = models.TextField()


class Incident(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='incidents')
    description = models.TextField()
    solution = models.TextField()

    def __str__(self):
        return f"Инцидент: {self.description[:50]}"


class Rating(models.Model):
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE)
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    score = models.IntegerField()


class IncidentRating(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    score = models.IntegerField()


# Оценка Z (оценка процесса)
class ZAssessment(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)  # <-- добавлено
    label = models.CharField(max_length=100)  # Например: "Выполнил"
    value = models.FloatField()

    def __str__(self):
        return f"Z: {self.label} = {self.value}"


# Оценка критерия
class CriteriaAssessment(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)  # <-- добавлено
    label = models.CharField(max_length=100)  # Например: "3 - Полностью"
    value = models.FloatField()

    def __str__(self):
        return f"Критерий: {self.label} = {self.value}"


# Тип проверки
class CheckMethod(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE, default=4)  # <-- добавлено
    label = models.CharField(max_length=100)  # Например: "Наблюдение"
    coefficient = models.FloatField()

    def __str__(self):
        return f"Метод: {self.label} = {self.coefficient}"


class ChecklistFilling(models.Model):
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE)
    employee = models.CharField(max_length=100)  #Имя сотрудника
    filled_by = models.ForeignKey(User, on_delete=models.CASCADE)  # кто заполняет
    status = models.CharField(max_length=20, choices=[('draft', 'В процессе'), ('completed', 'Завершен')])
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    json_data = models.JSONField()


class CompetencyChecklistFilling(models.Model):
    checklist =models.ForeignKey(Checklist, on_delete=models.CASCADE)
    filling = models.ForeignKey(ChecklistFilling, on_delete=models.CASCADE)
    competency_json = models.JSONField()

class ResultsChecklistFilling(models.Model):
    filling = models.ForeignKey(ChecklistFilling, on_delete=models.CASCADE)
    competencies_json = models.JSONField()
    competencies_summary_json = models.JSONField()
    processes_data = models.JSONField()
    processes_summary = models.JSONField()

class ProcessAssessment(models.Model):
    filling = models.ForeignKey(ChecklistFilling, on_delete=models.CASCADE)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    z_assessment = models.ForeignKey(ZAssessment, on_delete=models.SET_NULL, null=True)


class CriterionAssessmentEntry(models.Model):
    filling = models.ForeignKey(ChecklistFilling, on_delete=models.CASCADE)
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE)
    assessment = models.ForeignKey(CriteriaAssessment, on_delete=models.SET_NULL, null=True)
    method = models.ForeignKey(CheckMethod, on_delete=models.SET_NULL, null=True)


class IncidentAssessmentEntry(models.Model):
    filling = models.ForeignKey(ChecklistFilling, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    assessment = models.ForeignKey(CriteriaAssessment, on_delete=models.SET_NULL, null=True)
    method = models.ForeignKey(CheckMethod, on_delete=models.SET_NULL, null=True)
