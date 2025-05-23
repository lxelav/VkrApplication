# Generated by Django 5.1.7 on 2025-05-04 20:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_remove_process_group_checkmethod_company_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChecklistFilling',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('draft', 'В процессе'), ('completed', 'Завершен')], max_length=20)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('checklist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.checklist')),
                ('filled_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CriterionAssessmentEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assessment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.criteriaassessment')),
                ('criterion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.criterion')),
                ('filling', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.checklistfilling')),
                ('method', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.checkmethod')),
            ],
        ),
        migrations.CreateModel(
            name='IncidentAssessmentEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assessment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.criteriaassessment')),
                ('filling', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.checklistfilling')),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.incident')),
                ('method', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.checkmethod')),
            ],
        ),
        migrations.CreateModel(
            name='ProcessAssessment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filling', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.checklistfilling')),
                ('process', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.process')),
                ('z_assessment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.zassessment')),
            ],
        ),
    ]
