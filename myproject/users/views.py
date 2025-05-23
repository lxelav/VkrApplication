import json

from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import authenticate, login, get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from .forms import CustomUserCreationForm, CustomUserChangeForm, CompanyForm
from django.contrib import messages
from .models import Company, JobTitle, Checklist, CompetencyMatrix, Competency, Process, Criterion, Rating, Incident, \
    IncidentRating, ProcessGroup, ZAssessment, CriteriaAssessment, CheckMethod, ProcessSubGroup, ChecklistFilling, \
    ProcessAssessment, CriterionAssessmentEntry, IncidentAssessmentEntry, CompetencyChecklistFilling, ResultsChecklistFilling

# Определяем меню для каждой роли
ROLE_MENU = {
    'admin': [
        {'name': 'Предприятия', 'href': '/companies/'},
        {'name': 'Пользователи', 'href': '/users/'},
    ],
    'tech_lead': [
        {'name': 'Мои предприятия', 'href': '/companies/'},
    ],
    'methodist': [
        {'name': 'Предприятие', 'href': f'/companies/'},
    ],
    'expert': [
        {'name': 'Предприятие', 'href': f'/companies/'},
    ]
}

User = get_user_model()

def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')  # Перенаправляем на начальную страницу
        return HttpResponse("Ошибка авторизации", status=401)
    return render(request, 'login.html')

@login_required
def dashboard(request):
    user = request.user
    user_role = request.user.role

    # Получаем компанию (если одна)
    company = user.company if hasattr(user, 'company') else None

    menu_items = []

    if user_role == 'methodist':
        if company:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{company.id}/'}]
        else:
            menu_items = [{'name': 'Предприятие еще не назначено', 'href': f'/dashboard'}]
    elif user_role == 'expert':
        if company:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{company.id}/'}]
        else:
            menu_items = [{'name': 'Предприятие еще не назначено', 'href': f'/dashboard'}]
    else:
        menu_items = ROLE_MENU.get(user_role, [])

    context = {
        'menu_items': menu_items,
        'username': user.username,
        'role': user_role
    }

    return render(request, 'dashboard.html', context)

@login_required
def users_list(request):
    if request.user.role != 'admin':
        return render(request, '403.html')

    users = User.objects.all()

    user_role = request.user.role
    menu_items = ROLE_MENU.get(user_role, [])

    context = {'users': users, 'menu_items': menu_items, 'username': request.user.username}
    return render(request, 'users_list.html', context)

def user_create(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Пользователь успешно создан.")
            return redirect('users_list')
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
    else:
        form = CustomUserCreationForm()

    user_role = request.user.role
    menu_items = ROLE_MENU.get(user_role, [])

    return render(request, 'user_create.html', {
        'form': form,
        'title': 'Создать пользователя',
        'menu_items': menu_items
    })

def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users_list')
    else:
        form = CustomUserChangeForm(instance=user)

    user_role = request.user.role
    menu_items = ROLE_MENU.get(user_role, [])

    return render(request, 'user_edit.html', {'form': form, 'title': 'Редактировать пользователя', 'menu_items': menu_items})

def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('users_list')

    user_role = request.user.role
    menu_items = ROLE_MENU.get(user_role, [])
    return render(request, 'user_confirm_delete.html', {'user': user, 'menu_items': menu_items})

def company_list(request):
    user = request.user
    user_role = user.role
    menu_items = ROLE_MENU.get(user_role, [])

    if user_role == 'tech_lead':
        companies = Company.objects.filter(tech_lead=user)
    else:
        companies = Company.objects.all()

    return render(request, 'company_list_update.html', {
        'user_role': user_role,
        'companies': companies,
        'menu_items': menu_items,
        'title': 'Предприятия',
    })

def company_detail(request, company_id):
    company = get_object_or_404(Company, id=company_id)

    users = company.users.all()

    roles = set(user.role for user in users)
    users_by_role = {role: [] for role in roles}

    for user in users:
        users_by_role[user.role].append(user)

    if request.method == 'POST':
        new_job_title = request.POST.get('job_title_name')
        if new_job_title:
            JobTitle.objects.create(name=new_job_title, company=company)
            messages.success(request, "Должность успешно добавлена.")
            return redirect('company_detail', company_id=company.id)
        else:
            messages.error(request, "Название должности не может быть пустым.")

    # Получаем должности компании
    job_titles = JobTitle.objects.filter(company=company)

    # Получаем чек-листы для каждой должности
    job_checklists = {}
    for job_title in job_titles:
        checklists = Checklist.objects.filter(company=company, job_title=job_title)
        job_checklists[job_title.id] = checklists

    print(job_checklists)

    # Получаем оценки
    z_assessments = ZAssessment.objects.filter(company=company)
    criteria_assessments = CriteriaAssessment.objects.filter(company=company)
    check_methods = CheckMethod.objects.filter(company=company)

    user_role = request.user.role
    menu_items = []

    if user_role == 'methodist':
        if company:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{company.id}/'}]
    elif user_role == 'expert':
        if company:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{company.id}/'}]
    else:
        menu_items = ROLE_MENU.get(user_role, [])

    # Отправляем данные в шаблон
    return render(request, 'company_detail_update.html', {
        'company': company,
        'users_by_role': users_by_role,
        'menu_items': menu_items,
        'job_titles': job_titles,
        'job_checklists': job_checklists,
        'z_assessments': z_assessments,
        'criteria_assessments': criteria_assessments,
        'check_methods': check_methods,
    })

def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Предприятие успешно создано.')
            return redirect('company_list')
        else:
            messages.error(request, 'Произошла ошибка при создании предприятия.')
    else:
        form = CompanyForm()

    user_role = request.user.role
    menu_items = ROLE_MENU.get(user_role, [])
    return render(request, 'company_form.html', {
        'form': form,
        'title': 'Создать предприятие',
        'menu_items': menu_items,
    })

def company_edit(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('company_detail', company_id=company.id)
    else:
        form = CompanyForm(instance=company)

    user_role = request.user.role
    menu_items = ROLE_MENU.get(user_role, [])
    return render(request, 'company_edit_update.html', {'form': form, 'company': company, 'menu_items': menu_items,})

def company_delete(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST':
        company.delete()
        return redirect('company_list')

    return render(request, 'company_delete.html', {'company': company})

def edit_roles(request, company_id):
    # Проверяем, что пользователь — технический руководитель
    if request.user.role not in ('tech_lead', 'admin'):
        messages.error(request, "Доступ запрещён.")
        return redirect('company_list')

    # Получаем компанию, для которой редактируются роли
    company = get_object_or_404(Company, id=company_id)

    # Получаем всех экспертов и методистов этой компании
    experts = User.objects.filter(company=company, role='expert')
    methodists = User.objects.filter(company=company, role='methodist')

    if request.method == 'POST':
        # Обновляем роли пользователей, основываясь на данных из формы
        for user in experts | methodists:
            new_role = request.POST.get(f'role_{user.id}')
            if new_role and new_role in dict(User.ROLE_CHOICES).keys():
                user.role = new_role
                user.save()
        messages.success(request, "Роли пользователей обновлены.")



        return redirect('edit_roles', company_id=company.id)

    menu_items = ROLE_MENU.get(request.user.role, [])

    return render(request, 'edit_roles.html', {
        'company': company,
        'experts': experts,
        'methodists': methodists,
        'role_choices': User.ROLE_CHOICES,
        'menu_items': menu_items,
    })

def create_checklist(request, company_id, job_title_id):
    user_role = request.user.role
    menu_items = ROLE_MENU.get(user_role, [])

    company = get_object_or_404(Company, id=int(company_id))
    job_title = get_object_or_404(JobTitle, id=job_title_id, company=company)

    return render(request, 'checklist.html', {
        'menu_items': menu_items,
        'company_id': company_id,
        'job_title_id': job_title_id,
        'job_title_name': job_title.name,
    })

@csrf_exempt
def save_all(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            checklist_data = data.get("checklist")
            matrix_data = data.get("matrix")

            print('save_all: ', data)

            job_title_id = data.get("jobTitleId")
            company_id = data.get("companyId")

            company = Company.objects.get(id=company_id)
            job_title = JobTitle.objects.get(id=job_title_id)

            # 1. Сохраняем чек-лист
            checklist = Checklist.objects.create(
                title=data.get('checklistTitle'),
                company=company,
                job_title=job_title,
                data=checklist_data,
                timestamp=data.get('timestamp')
            )

            # 2. Сохраняем матрицу компетенций
            matrix = CompetencyMatrix.objects.create(
                job_title=job_title,
                checklist=checklist,
                created_at=data.get("timestamp")
            )

            # 3. Сохраняем компетенции
            competency_objs = []
            for comp_name in matrix_data.get('competencies', []):
                competency = Competency.objects.create(name=comp_name, matrix=matrix)
                competency_objs.append(competency)

            # 4. Сохраняем группы, подгруппы, процессы, критерии, инциденты
            process_map = {}  # process_id: (proc_obj, [criteria], [incidents])
            for group in matrix_data.get('groups', []):
                group_obj = ProcessGroup.objects.create(name=group['name'], matrix=matrix)

                for subgroup in group.get('subgroups', []):
                    subgroup_obj = ProcessSubGroup.objects.create(name=subgroup['name'], group=group_obj)

                    for proc in subgroup.get('processes', []):
                        proc_obj = Process.objects.create(
                            name=proc['name'],
                            matrix=matrix,
                            subgroup=subgroup_obj  # теперь к подгруппе
                        )

                        # критерии
                        criteria_list = []
                        for idx, crit_text in enumerate(proc.get('criteria', '').split(';')):
                            crit_text = crit_text.strip()
                            if crit_text:
                                criterion = Criterion.objects.create(process=proc_obj, text=crit_text)
                                criteria_list.append(criterion)

                        # инциденты
                        incident_list = []
                        for inc in proc.get('incidents', []):
                            incident = Incident.objects.create(
                                process=proc_obj,
                                description=inc.get('description', '').strip(),
                                solution=inc.get('solution', '').strip()
                            )
                            incident_list.append(incident)

                        process_map[proc['id']] = (proc_obj, criteria_list, incident_list)

            ratings = matrix_data.get('ratings', {})
            for group_id, subgroups_dict in ratings.items():
                for subgroup_id, process_dict in subgroups_dict.items():
                    for process_key, comp_scores in process_dict.items():
                        if '-crit-' in process_key:
                            # Рейтинг критерия
                            process_id, _, crit_index = process_key.partition('-crit-')
                            crit_index = int(crit_index)

                            proc_tuple = process_map.get(process_id)
                            if not proc_tuple:
                                continue

                            _, crit_list, _ = proc_tuple
                            if crit_index >= len(crit_list):
                                continue

                            criterion = crit_list[crit_index]
                            for comp_idx_str, score in comp_scores.items():
                                comp_idx = int(comp_idx_str)
                                if comp_idx < len(competency_objs):
                                    competency = competency_objs[comp_idx]
                                    Rating.objects.create(criterion=criterion, competency=competency, score=score)

                        elif '-inc-' in process_key:
                            # Рейтинг инцидента
                            process_id, _, inc_index = process_key.partition('-inc-')
                            inc_index = int(inc_index)

                            proc_tuple = process_map.get(process_id)
                            if not proc_tuple:
                                continue

                            _, _, inc_list = proc_tuple
                            if inc_index >= len(inc_list):
                                continue

                            incident = inc_list[inc_index]
                            for comp_idx_str, score in comp_scores.items():
                                comp_idx = int(comp_idx_str)
                                if comp_idx < len(competency_objs):
                                    competency = competency_objs[comp_idx]
                                    IncidentRating.objects.create(incident=incident, competency=competency, score=score)



            return JsonResponse({"status": "ok"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "method not allowed"}, status=405)

def save_assessments(request, company_id):
    company = get_object_or_404(Company, id=company_id)

    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('z_'):
                ZAssessment.objects.filter(id=key[2:], company=company).update(value=value)
            elif key.startswith('c_'):
                CriteriaAssessment.objects.filter(id=key[2:], company=company).update(value=value)
            elif key.startswith('m_'):
                CheckMethod.objects.filter(id=key[2:], company=company).update(coefficient=value)

        messages.success(request, "Оценки сохранены.")
        return redirect(request.path)

    return redirect('company_detail', company_id=company_id)

def load_default_assessments(request, company_id):
    company = get_object_or_404(Company, id=company_id)

    # Удаляем старые значения (если нужно)
    ZAssessment.objects.filter(company=company).delete()
    CriteriaAssessment.objects.filter(company=company).delete()
    CheckMethod.objects.filter(company=company).delete()

    # Стандартные значения
    default_z = [
        {"label": "Не проверен", "value": 0},
        {"label": "Выполнил", "value": 1},
        {"label": "Не выполнил", "value": 0},
    ]

    default_criteria = [
        {"label": "Не проверен", "value": 0},
        {"label": "Полностью", "value": 1},
        {"label": "С недостатками", "value": 0.65},
        {"label": "Допустимо", "value": 0.3},
        {"label": "Недопустимо", "value": 0},
    ]

    default_methods = [
        {"label": "Не ясен", "coefficient": 0.1},
        {"label": "Наблюдение", "coefficient": 1},
        {"label": "Практика", "coefficient": 0.9},
        {"label": "Тест", "coefficient": 0.5},
        {"label": "Опрос", "coefficient": 0.3},
    ]

    for item in default_z:
        ZAssessment.objects.create(company=company, label=item["label"], value=item["value"])
    for item in default_criteria:
        CriteriaAssessment.objects.create(company=company, label=item["label"], value=item["value"])
    for item in default_methods:
        CheckMethod.objects.create(company=company, label=item["label"], coefficient=item["coefficient"])

    return redirect('company_detail', company_id=company_id)

def checklist_detail(request, checklist_id):
    user_role = request.user.role
    menu_items = []

    checklist = get_object_or_404(Checklist, id=checklist_id)
    if user_role == 'methodist':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    elif user_role == 'expert':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    else:
        menu_items = ROLE_MENU.get(user_role, [])

    company = get_object_or_404(Company, id=checklist.company_id)
    job_title = get_object_or_404(JobTitle, id=checklist.job_title_id, company=company)

    fillings = ChecklistFilling.objects.filter(checklist=checklist)

    completed = fillings.filter(status='completed')
    in_progress = fillings.filter(status='draft')

    return render(request, 'checklist_detail.html', {
        'checklist': checklist,
        'menu_items': menu_items,
        'job_title': job_title.name.lower(),
        "completed_fillings": completed,
        "in_progress_fillings": in_progress,
    })

def evaluate_checklist(request, checklist_id):
    user_role = request.user.role
    menu_items = []

    checklist = get_object_or_404(Checklist, id=checklist_id)
    if user_role == 'methodist':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    elif user_role == 'expert':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    else:
        menu_items = ROLE_MENU.get(user_role, [])

    company = get_object_or_404(Company, id=checklist.company_id)
    job_title = get_object_or_404(JobTitle, id=checklist.job_title_id, company=company)

    # предполагается, что поле с JSON называется `data` (переименуй, если нужно)
    checklist_data = checklist.data  # это уже Python-объект, если JSONField
    if isinstance(checklist_data, str):
        checklist_data = json.loads(checklist_data)

    context = {
        'checklist_json': json.dumps({
            'checklistId': checklist.id,
            'jobTitle': job_title.name,
            'groups': checklist_data,
        }),
        'menu_items': menu_items,
        'jobTitle': job_title.name.lower(),
        'evaluation_date': timezone.now(),
        'checklistId': checklist.id,
        'companyId': company.id,
        'fillingId': -100,
        'filling_json': {},
    }

    return render(request, 'checklist_eva.html', context)

@csrf_exempt
def submit_evaluation(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            if data.get('fillingId') != -100:
                filling = get_object_or_404(ChecklistFilling, id=data.get('fillingId'))
                filling.delete()

            checklist_id = data.get('checklistId')
            checklist = Checklist.objects.get(id=checklist_id)
            matrix = CompetencyMatrix.objects.get(checklist=checklist)
            company = get_object_or_404(Company, id=data.get('companyId'))

            filled_by = request.user if request.user.is_authenticated else User.objects.first()  # fallback
            employee_name = data.get('employeeName', 'Без имени')
            status = data.get('status', 'draft')
            finished_at = parse_datetime(data['evaluationDate']) if status == 'completed' else None

            filling = ChecklistFilling.objects.create(
                checklist=checklist,
                employee=employee_name,
                filled_by=filled_by,
                status=status,
                finished_at=finished_at,
                json_data=data.get('groups', []),
            )

            print('ya tyt')

            # Удалить предыдущие черновики по этому чек-листу и сотруднику
            if status == 'completed':
                ChecklistFilling.objects.filter(
                    checklist=checklist,
                    employee=employee_name,
                    status='draft'
                ).exclude(id=filling.id).delete()

            try:
                for group in data.get('groups', []):
                    print('group: ', group)
                    for subgroup in group.get('subgroups', []):
                        print()
                        print('subgroup: ', subgroup)
                        for proc in subgroup.get('processes', []):
                            print()
                            print('proc: ', proc)
                            # Ищем процесс в БД
                            process_obj = Process.objects.filter(name=proc.get('name'), matrix=matrix).first()

                            label_za = 'Не проверен' if proc.get('status') == 'not-checked' else \
                                'Выполнил' if proc.get('status') == 'completed' else 'Не выполнил'
                            z_assessment = ZAssessment.objects.filter(label=label_za, company=company).first()

                            if process_obj:
                                ProcessAssessment.objects.create(
                                    filling=filling,
                                    process=process_obj,
                                    z_assessment=z_assessment
                                )

                                print('tyt2')

                                # Обработка критериев
                                for crit in proc.get('criteria', []):
                                    print(crit, crit.get('text'), crit.get('rating'), crit.get('method'))
                                    crit_obj = Criterion.objects.filter(text=crit.get('text'), process_id=process_obj).first()

                                    label_ass = 'Не проверен' if crit.get('rating') == -1 else 'Недопустимо' if crit.get('rating') == 0 else 'Допустимо' if crit.get('rating') == 1 else 'С недостатками' if crit.get('rating') == 2 else 'Полностью'
                                    label_method = 'Не ясен' if crit.get('method') == '' else 'Наблюдение' if crit.get('method') == 'observation' else 'Практика' if crit.get('method') == 'practice' else 'Тест' if crit.get('method') == 'test' else 'Опрос'

                                    assessment = CriteriaAssessment.objects.filter(label=label_ass, company=company).first()
                                    method = CheckMethod.objects.filter(label=label_method, company=company).first()
                                    if crit_obj:
                                        CriterionAssessmentEntry.objects.create(
                                            filling=filling,
                                            criterion=crit_obj,
                                            assessment=assessment,
                                            method=method
                                        )
                                print('tyt3')

                                # Обработка инцидентов
                                for inc in proc.get('incidents', []):
                                    inc_obj = Incident.objects.filter(description=inc.get('description'), solution=inc.get('solution'), process_id=process_obj).first()

                                    label_ass = 'Не проверен' if crit.get(
                                        'rating') == -1 else 'Недопустимо' if crit.get(
                                        'rating') == 0 else 'Допустимо' if crit.get(
                                        'rating') == 1 else 'С недостатками' if crit.get('rating') == 2 else 'Полностью'
                                    label_method = 'Не ясен' if crit.get('method') == '' else 'Наблюдение' if crit.get(
                                        'method') == 'observation' else 'Практика' if crit.get(
                                        'method') == 'practice' else 'Тест' if crit.get('method') == 'test' else 'Опрос'

                                    assessment = CriteriaAssessment.objects.filter(label=label_ass,
                                                                                   company=company).first()
                                    method = CheckMethod.objects.filter(label=label_method, company=company).first()

                                    if inc_obj:
                                        IncidentAssessmentEntry.objects.create(
                                            filling=filling,
                                            incident=inc_obj,
                                            assessment=assessment,
                                            method=method
                                        )

                                        print('tyt4')
            except Exception as e:
                print(e)


            try:
                # функция для подсчета и сохорания результатов в бд по filling(-y)
                if status == 'completed':
                    calculate_checklist_results(filling, checklist)
            except Exception as e:
                print(e)

            redirect_url = reverse('checklist_detail', args=[checklist.id])  # Название своего view/url

            return JsonResponse({'message': 'Оценка успешно сохранена', 'redirect_url': redirect_url}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

def calculate_checklist_results(filling, checklist):
    # Тут оценка компетенций
    matrix = get_object_or_404(CompetencyMatrix, checklist_id=checklist)

    comp_list = Competency.objects.filter(matrix_id=matrix)
    dict_comp = {}
    dict_comp_sum = {}
    dict_comp_polnota = {}
    dict_comp_tochnost = {}
    for competency in comp_list:
        dict_comp[competency.name] = []
        dict_comp_sum[competency.name] = []
        dict_comp_polnota[competency.name] = 0
        dict_comp_tochnost[competency.name] = []

    data_process = []
    all_process_score = {'temp111': 0,
                         'temp222': 0,
                         'temp333': 0,
                         'temp444': 0,
                         'temp555': 0,
                         'temp_all_all_all': 0,
                         'temp111_accuracy': 0,
                         'temp222_accuracy': 0,
                         'temp333_accuracy': 0,
                         'temp444_accuracy': 0,
                         'temp555_accuracy': 0,
                         'temp_all_all_all_accuracy': 0,
                         "totalPoints": 0,
                         "totalScore": 0,
                         "totalCompleteness": 0,
                         "totalAccuracy": 0}
    try:
        proc_groups = ProcessGroup.objects.filter(
            matrix=matrix
        ).prefetch_related(
            Prefetch('subgroups',
                     queryset=ProcessSubGroup.objects.prefetch_related(
                         Prefetch('processes',
                                  queryset=Process.objects.prefetch_related(
                                      'incidents',
                                      'criteria',
                                      'processassessment_set'
                                  )
                                  )
                     )
                     )
        )

        for i, group in enumerate(proc_groups):
            data_process.append({'id': i + 1,
                                 'name': group.name,
                                 'metrics': {
                                     # Z metric:
                                     "total": 0,
                                     "checked": 0,
                                     "checkedPercent": "",
                                     "completed": 0,
                                     "completedPercent": "",

                                     'temp1': 0,
                                     'temp2': 0,
                                     'temp3': 0,
                                     'temp4': 0,
                                     'temp5': 0,
                                     'temp_all': 0,
                                     'temp1_accuracy': 0,
                                     'temp2_accuracy': 0,
                                     'temp3_accuracy': 0,
                                     'temp4_accuracy': 0,
                                     'temp5_accuracy': 0,
                                     'temp_all_accuracy': 0,
                                     # CriteriaQuality
                                     "qualityScore": "0",
                                     "qualityCompleteness": "0",
                                     "qualityAccuracy": "0",

                                     'temp11': 0,
                                     'temp22': 0,
                                     'temp33': 0,
                                     'temp44': 0,
                                     'temp55': 0,
                                     'temp_all_all': 0,
                                     'temp11_accuracy': 0,
                                     'temp22_accuracy': 0,
                                     'temp33_accuracy': 0,
                                     'temp44_accuracy': 0,
                                     'temp55_accuracy': 0,
                                     'temp_all_all_accuracy': 0,
                                     # Incident
                                     "incidentScore": "0",
                                     "incidentCompleteness": "0",
                                     "incidentAccuracy": "0",

                                     'temp111': 0,
                                     'temp222': 0,
                                     'temp333': 0,
                                     'temp444': 0,
                                     'temp555': 0,
                                     'temp_all_all_all': 0,
                                     'temp111_accuracy': 0,
                                     'temp222_accuracy': 0,
                                     'temp333_accuracy': 0,
                                     'temp444_accuracy': 0,
                                     'temp555_accuracy': 0,
                                     'temp_all_all_all_accuracy': 0,
                                     # Total
                                     "totalPoints": "0",
                                     "totalScore": "0",
                                     "totalCompleteness": "0",
                                     "totalAccuracy": "0"
                                 },
                                 'processes': []
                                 })

            for j, subGroup in enumerate(group.subgroups.all()):
                processes = subGroup.processes.all()
                process_count = processes.count()
                # Добавляем подгруппу для группы по index: i:
                data_process[i]['processes'].append(
                    {'id': j + 1,
                     'name': subGroup.name,
                     'metrics': {
                         # Z-metric
                         "total": process_count,
                         "checked": 0,
                         "checkedPercent": "",
                         "completed": 0,
                         "completedPercent": "",

                         'temp1': 0,
                         'temp2': 0,
                         'temp3': 0,
                         'temp4': 0,
                         'temp5': 0,
                         'temp_all': 0,
                         'temp1_accuracy': 0,
                         'temp2_accuracy': 0,
                         'temp3_accuracy': 0,
                         'temp4_accuracy': 0,
                         'temp5_accuracy': 0,
                         'temp_all_accuracy': 0,
                         # CriteriaQuality
                         "qualityScore": "0",
                         "qualityCompleteness": "0",
                         "qualityAccuracy": "0",

                         'temp11': 0,
                         'temp22': 0,
                         'temp33': 0,
                         'temp44': 0,
                         'temp55': 0,
                         'temp_all_all': 0,
                         'temp11_accuracy': 0,
                         'temp22_accuracy': 0,
                         'temp33_accuracy': 0,
                         'temp44_accuracy': 0,
                         'temp55_accuracy': 0,
                         'temp_all_all_accuracy': 0,
                         # Incident
                         "incidentScore": "0",
                         "incidentCompleteness": "0",
                         "incidentAccuracy": "0",

                         # Total
                         'temp111': 0,
                         'temp222': 0,
                         'temp333': 0,
                         'temp444': 0,
                         'temp555': 0,
                         'temp_all_all_all': 0,
                         'temp111_accuracy': 0,
                         'temp222_accuracy': 0,
                         'temp333_accuracy': 0,
                         'temp444_accuracy': 0,
                         'temp555_accuracy': 0,
                         'temp_all_all_all_accuracy': 0,
                         "totalPoints": "0",
                         "totalScore": "0",
                         "totalCompleteness": "0",
                         "totalAccuracy": "0"
                     },
                     'criteria': [],
                     })

                data_process[i]['metrics']['total'] += process_count

                for k, process in enumerate(processes):
                    # Считаю для оценки процессов(достаю Оценку процесса из бд и смотрю че там написано)
                    temp_obj = get_object_or_404(ProcessAssessment, process_id=process, filling_id=filling)
                    z_assessment = get_object_or_404(ZAssessment, id=temp_obj.z_assessment_id)

                    if z_assessment.label != 'Не проверен':
                        data_process[i]['processes'][j]['metrics']['checked'] += 1
                        data_process[i]['metrics']['checked'] += 1

                    if z_assessment.label == 'Выполнил':
                        data_process[i]['processes'][j]['metrics']['completed'] += 1
                        data_process[i]['metrics']['completed'] += 1

                    # Добавляю процесс:
                    data_process[i]['processes'][j]['criteria'].append({
                        'id': k + 1,
                        'name': process.name,
                        'yes': 'true' if z_assessment.label == 'Выполнил' else 'false' if z_assessment.label == 'Не выполнил' else '-',
                        'metrics': {
                            'temp1': 0,
                            'temp2': 0,
                            'temp3': 0,
                            'temp4': 0,
                            'temp5': 0,
                            'temp_all': 0,
                            'temp1_accuracy': 0,
                            'temp2_accuracy': 0,
                            'temp3_accuracy': 0,
                            'temp4_accuracy': 0,
                            'temp5_accuracy': 0,
                            'temp_all_accuracy': 0,
                            "score": "",
                            "completeness": "",
                            "accuracy": "",

                            'temp11': 0,
                            'temp22': 0,
                            'temp33': 0,
                            'temp44': 0,
                            'temp55': 0,
                            'temp_all_all': 0,
                            'temp11_accuracy': 0,
                            'temp22_accuracy': 0,
                            'temp33_accuracy': 0,
                            'temp44_accuracy': 0,
                            'temp55_accuracy': 0,
                            'temp_all_all_accuracy': 0,
                            "incidentScore": "",
                            "incidentCompleteness": "",
                            "incidentAccuracy": "",

                            'temp111': 0,
                            'temp222': 0,
                            'temp333': 0,
                            'temp444': 0,
                            'temp555': 0,
                            'temp_all_all_all': 0,
                            'temp111_accuracy': 0,
                            'temp222_accuracy': 0,
                            'temp333_accuracy': 0,
                            'temp444_accuracy': 0,
                            'temp555_accuracy': 0,
                            'temp_all_all_all_accuracy': 0,
                            "totalPoints": "",
                            "totalScore": "",
                            "totalCompleteness": "",
                            "totalAccuracy": "100"
                        },
                    }
                    )

                    criterions = Criterion.objects.filter(process=process)
                    incidents = Incident.objects.filter(process=process)

                    for criterion in criterions:
                        temp = CriterionAssessmentEntry.objects.filter(filling_id=filling,
                                                                       criterion_id=criterion).first()
                        expert_rating_criterion = get_object_or_404(CriteriaAssessment, id=temp.assessment_id)
                        expert_method_criterion = get_object_or_404(CheckMethod, id=temp.method_id)

                        if expert_rating_criterion.label == 'Полностью':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1'] += 1
                        elif expert_rating_criterion.label == 'С недостатками':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2'] += 1
                        elif expert_rating_criterion.label == 'Допустимо':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3'] += 1
                        elif expert_rating_criterion.label == 'Недопустимо':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4'] += 1
                        else:
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5'] += 1

                        if expert_rating_criterion.label != 'Не проверен':
                            data_process[i]['processes'][j]['criteria'][k]['metrics'][
                                'temp_all'] += expert_rating_criterion.value

                        if expert_method_criterion.label == 'Наблюдение':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1_accuracy'] += 1
                        elif expert_method_criterion.label == 'Практика':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2_accuracy'] += 1
                        elif expert_method_criterion.label == 'Тест':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3_accuracy'] += 1
                        elif expert_method_criterion.label == 'Опрос':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4_accuracy'] += 1
                        elif expert_method_criterion.label == 'Не ясен':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5_accuracy'] += 1

                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'temp_all_accuracy'] += expert_method_criterion.coefficient

                    for incident in incidents:
                        temp = IncidentAssessmentEntry.objects.filter(filling_id=filling, incident_id=incident).first()
                        expert_rating_incident = get_object_or_404(CriteriaAssessment, id=temp.assessment_id)
                        expert_method_incident = get_object_or_404(CheckMethod, id=temp.method_id)

                        if expert_rating_incident.label == 'Полностью':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11'] += 1
                        elif expert_rating_incident.label == 'С недостатками':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22'] += 1
                        elif expert_rating_incident.label == 'Допустимо':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33'] += 1
                        elif expert_rating_incident.label == 'Недопустимо':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44'] += 1
                        else:
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55'] += 1

                        if expert_rating_incident.label != 'Не проверен':
                            data_process[i]['processes'][j]['criteria'][k]['metrics'][
                                'temp_all_all'] += expert_rating_incident.value

                        if expert_method_incident.label == 'Наблюдение':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11_accuracy'] += 1
                        elif expert_method_incident.label == 'Практика':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22_accuracy'] += 1
                        elif expert_method_incident.label == 'Тест':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33_accuracy'] += 1
                        elif expert_method_incident.label == 'Опрос':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44_accuracy'] += 1
                        elif expert_method_incident.label == 'Не ясен':
                            data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55_accuracy'] += 1

                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'temp_all_all_accuracy'] += expert_method_incident.coefficient

                    # теперь для процесса посчитаю всего:
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp111'] = \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1'] + \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp222'] = \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2'] + \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp333'] = \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3'] + \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp444'] = \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4'] + \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp555'] = \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5'] + \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_all'] = \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all'] + \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all']

                    # теперь для процесса посчитаю всего:
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp111_accuracy'] = \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1_accuracy'] + \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11_accuracy']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp222_accuracy'] = \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2_accuracy'] + \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22_accuracy']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp333_accuracy'] = \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3_accuracy'] + \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33_accuracy']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp444_accuracy'] = \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4_accuracy'] + \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44_accuracy']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp555_accuracy'] = \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5_accuracy'] + \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55_accuracy']
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_all_accuracy'] = \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_accuracy'] + \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_accuracy']


                    data_process[i]['processes'][j]['criteria'][k]['metrics']['totalPoints'] = \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_all']

                    sum_temp = (data_process[i]['processes'][j]['criteria'][k]['metrics']['temp111'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp222'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp333'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp444'])
                    if sum_temp != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['totalScore'] = f"{round(data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_all'] / sum_temp, 1) * 100}"
                    else:
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['totalScore'] = '0'

                    # Полнота
                    if sum_temp + data_process[i]['processes'][j]['criteria'][k]['metrics']['temp555'] != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'totalCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['processes'][j]['criteria'][k]['metrics']['temp555']), 1) * 100}"

                    # Точность
                    sum_temp = (data_process[i]['processes'][j]['criteria'][k]['metrics']['temp111_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp222_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp333_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp444_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp555_accuracy'])
                    if sum_temp != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'totalAccuracy'] = f"{round(data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_all_accuracy'] / sum_temp, 1) * 100}"
                    else:
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['totalAccuracy'] = '0'

                    # Тут считается критерии качества и инцинденты для процесса
                    # Оценка
                    sum_temp = (data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4'])
                    if sum_temp != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'score'] = f"{round(data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all'] / sum_temp, 1) * 100}"
                    else:
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['score'] = '0'

                    # Полнота
                    if sum_temp + data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5'] != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'completeness'] = f"{round(sum_temp / (sum_temp + data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5']), 1) * 100}"

                    # Точность
                    sum_temp = (data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5_accuracy'])
                    if sum_temp != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'accuracy'] = f"{round(data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_accuracy'] / sum_temp, 1) * 100}"
                    else:
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['accuracy'] = '0'

                    # Оценка inc
                    sum_temp = (data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44'])
                    if sum_temp != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'incidentScore'] = f"{round(data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all'] / sum_temp, 1) * 100}"
                    else:
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['incidentScore'] = '0'

                    # Полнота inc
                    if sum_temp + data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55'] != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'incidentCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55']), 1) * 100}"

                    # Точность inc
                    sum_temp = (data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44_accuracy'] +
                                data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55_accuracy'])
                    if sum_temp != 0:
                        data_process[i]['processes'][j]['criteria'][k]['metrics'][
                            'incidentAccuracy'] = f"{round(data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_accuracy'] / sum_temp, 1) * 100}"
                    else:
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['incidentAccuracy'] = '0'

                    # Тут данные по критериям качества/inc добвляем в подгруппу
                    # оценка и полнота
                    data_process[i]['processes'][j]['metrics']['temp1'] += \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1']
                    data_process[i]['processes'][j]['metrics']['temp2'] += \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2']
                    data_process[i]['processes'][j]['metrics']['temp3'] += \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3']
                    data_process[i]['processes'][j]['metrics']['temp4'] += \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4']
                    data_process[i]['processes'][j]['metrics']['temp5'] += \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5']
                    data_process[i]['processes'][j]['metrics']['temp_all'] += \
                    data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all']

                    # Точность
                    data_process[i]['processes'][j]['metrics']['temp1_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp1_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp2_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp2_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp3_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp3_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp4_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp4_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp5_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp5_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp_all_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_accuracy']

                    # оценка и полнота inc
                    data_process[i]['processes'][j]['metrics']['temp11'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11']
                    data_process[i]['processes'][j]['metrics']['temp22'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22']
                    data_process[i]['processes'][j]['metrics']['temp33'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33']
                    data_process[i]['processes'][j]['metrics']['temp44'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44']
                    data_process[i]['processes'][j]['metrics']['temp55'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55']
                    data_process[i]['processes'][j]['metrics']['temp_all_all'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all']

                    # Точность inc
                    data_process[i]['processes'][j]['metrics']['temp11_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp11_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp22_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp22_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp33_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp33_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp44_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp44_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp55_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp55_accuracy']
                    data_process[i]['processes'][j]['metrics']['temp_all_all_accuracy'] += \
                        data_process[i]['processes'][j]['criteria'][k]['metrics']['temp_all_all_accuracy']

                    # оценка компетенций
                    for competency in comp_list:
                        for criterion in criterions:
                            matrix_rating_criterion = Rating.objects.filter(criterion_id=criterion,
                                                                            competency_id=competency).first()

                            temp = CriterionAssessmentEntry.objects.filter(filling_id=filling,
                                                                           criterion_id=criterion).first()
                            expert_rating_criterion = get_object_or_404(CriteriaAssessment, id=temp.assessment_id)
                            expert_method_criterion = get_object_or_404(CheckMethod, id=temp.method_id)

                            print(competency.name, ': ', matrix_rating_criterion.score * expert_rating_criterion.value,
                                  matrix_rating_criterion.score, expert_rating_criterion.value)

                            # оценка
                            dict_comp_sum[competency.name].append(matrix_rating_criterion.score)
                            dict_comp[competency.name].append(
                                matrix_rating_criterion.score * expert_rating_criterion.value)

                            # полнота:
                            print(criterion.text, matrix_rating_criterion.score, expert_rating_criterion.label)
                            if matrix_rating_criterion.score != 0 and expert_rating_criterion.label != 'Не проверен':
                                dict_comp_polnota[competency.name] += 1

                                # точность:
                                dict_comp_tochnost[competency.name].append(1 * expert_method_criterion.coefficient)

                        for incident in incidents:
                            matrix_rating_incident = IncidentRating.objects.filter(incident_id=incident,
                                                                                   competency_id=competency).first()

                            temp = IncidentAssessmentEntry.objects.filter(filling_id=filling,
                                                                          incident_id=incident).first()
                            expert_rating_incident = get_object_or_404(CriteriaAssessment, id=temp.assessment_id)
                            expert_method_incident = get_object_or_404(CheckMethod, id=temp.method_id)

                            # оценка
                            dict_comp_sum[competency.name].append(matrix_rating_incident.score)
                            dict_comp[competency.name].append(
                                matrix_rating_incident.score * expert_rating_incident.value)

                            # полнота:
                            print(incident.description, matrix_rating_incident.score, expert_rating_incident.label)
                            if matrix_rating_incident.score != 0 and expert_rating_incident.label != 'Не проверен':
                                dict_comp_polnota[competency.name] += 1

                                # точность:
                                dict_comp_tochnost[competency.name].append(1 * expert_method_incident.coefficient)

                # Это для Z-оценки в подгруппе
                if data_process[i]['processes'][j]['metrics']['total'] != 0 and \
                        data_process[i]['processes'][j]['metrics']['checked'] != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'checkedPercent'] = f"{round(data_process[i]['processes'][j]['metrics']['checked'] / data_process[i]['processes'][j]['metrics']['total'], 1) * 100}"
                    data_process[i]['processes'][j]['metrics'][
                        'completedPercent'] = f"{round(data_process[i]['processes'][j]['metrics']['completed'] / data_process[i]['processes'][j]['metrics']['checked'], 1) * 100}"
                else:
                    data_process[i]['processes'][j]['metrics']['checkedPercent'] = '0'
                    data_process[i]['processes'][j]['metrics']['completedPercent'] = '0'

                # теперь для подгруппы посчитаю всего:
                data_process[i]['processes'][j]['metrics']['temp111'] = \
                    data_process[i]['processes'][j]['metrics']['temp1'] + \
                    data_process[i]['processes'][j]['metrics']['temp11']
                data_process[i]['processes'][j]['metrics']['temp222'] = \
                    data_process[i]['processes'][j]['metrics']['temp2'] + \
                    data_process[i]['processes'][j]['metrics']['temp22']
                data_process[i]['processes'][j]['metrics']['temp333'] = \
                    data_process[i]['processes'][j]['metrics']['temp3'] + \
                    data_process[i]['processes'][j]['metrics']['temp33']
                data_process[i]['processes'][j]['metrics']['temp444'] = \
                    data_process[i]['processes'][j]['metrics']['temp4'] + \
                    data_process[i]['processes'][j]['metrics']['temp44']
                data_process[i]['processes'][j]['metrics']['temp555'] = \
                    data_process[i]['processes'][j]['metrics']['temp5'] + \
                    data_process[i]['processes'][j]['metrics']['temp55']
                data_process[i]['processes'][j]['metrics']['temp_all_all_all'] = \
                    data_process[i]['processes'][j]['metrics']['temp_all'] + \
                    data_process[i]['processes'][j]['metrics']['temp_all_all']

                # теперь для процесса посчитаю всего:
                data_process[i]['processes'][j]['metrics']['temp111_accuracy'] = \
                    data_process[i]['processes'][j]['metrics']['temp1_accuracy'] + \
                    data_process[i]['processes'][j]['metrics']['temp11_accuracy']
                data_process[i]['processes'][j]['metrics']['temp222_accuracy'] = \
                    data_process[i]['processes'][j]['metrics']['temp2_accuracy'] + \
                    data_process[i]['processes'][j]['metrics']['temp22_accuracy']
                data_process[i]['processes'][j]['metrics']['temp333_accuracy'] = \
                    data_process[i]['processes'][j]['metrics']['temp3_accuracy'] + \
                    data_process[i]['processes'][j]['metrics']['temp33_accuracy']
                data_process[i]['processes'][j]['metrics']['temp444_accuracy'] = \
                    data_process[i]['processes'][j]['metrics']['temp4_accuracy'] + \
                    data_process[i]['processes'][j]['metrics']['temp44_accuracy']
                data_process[i]['processes'][j]['metrics']['temp555_accuracy'] = \
                    data_process[i]['processes'][j]['metrics']['temp5_accuracy'] + \
                    data_process[i]['processes'][j]['metrics']['temp55_accuracy']
                data_process[i]['processes'][j]['metrics']['temp_all_all_all_accuracy'] = \
                    data_process[i]['processes'][j]['metrics']['temp_all_accuracy'] + \
                    data_process[i]['processes'][j]['metrics']['temp_all_all_accuracy']

                data_process[i]['processes'][j]['metrics']['totalPoints'] = \
                    data_process[i]['processes'][j]['metrics']['temp_all_all_all']

                sum_temp = (data_process[i]['processes'][j]['metrics']['temp111'] +
                            data_process[i]['processes'][j]['metrics']['temp222'] +
                            data_process[i]['processes'][j]['metrics']['temp333'] +
                            data_process[i]['processes'][j]['metrics']['temp444'])
                if sum_temp != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'totalScore'] = f"{round(data_process[i]['processes'][j]['metrics']['temp_all_all_all'] / sum_temp, 1) * 100}"
                else:
                    data_process[i]['processes'][j]['metrics']['totalScore'] = '0'

                # Полнота
                if sum_temp + data_process[i]['processes'][j]['metrics']['temp555'] != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'totalCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['processes'][j]['metrics']['temp555']), 1) * 100}"

                # Точность
                sum_temp = (data_process[i]['processes'][j]['metrics']['temp111_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp222_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp333_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp444_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp555_accuracy'])
                if sum_temp != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'totalAccuracy'] = f"{round(data_process[i]['processes'][j]['metrics']['temp_all_all_all_accuracy'] / sum_temp, 1) * 100}"
                else:
                    data_process[i]['processes'][j]['metrics']['totalAccuracy'] = '0'

                # Это для критериев качества/inc в подгруппе
                # (оценка)
                sum_temp = (data_process[i]['processes'][j]['metrics']['temp1'] +
                            data_process[i]['processes'][j]['metrics']['temp2'] +
                            data_process[i]['processes'][j]['metrics']['temp3'] +
                            data_process[i]['processes'][j]['metrics']['temp4'])
                if sum_temp != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'qualityScore'] = f"{round(data_process[i]['processes'][j]['metrics']['temp_all'] / sum_temp, 1) * 100}"
                else:
                    data_process[i]['processes'][j]['metrics']['qualityScore'] = '0'

                # Полнота
                if sum_temp + data_process[i]['processes'][j]['metrics']['temp5'] != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'qualityCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['processes'][j]['metrics']['temp5']), 1) * 100}"

                # Точность
                sum_temp = (data_process[i]['processes'][j]['metrics']['temp1_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp2_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp3_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp4_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp5_accuracy'])
                if sum_temp != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'qualityAccuracy'] = f"{round(data_process[i]['processes'][j]['metrics']['temp_all_accuracy'] / sum_temp, 1) * 100}"
                else:
                    data_process[i]['processes'][j]['metrics']['qualityAccuracy'] = '0'

                # (оценка) inc
                sum_temp = (data_process[i]['processes'][j]['metrics']['temp11'] +
                            data_process[i]['processes'][j]['metrics']['temp22'] +
                            data_process[i]['processes'][j]['metrics']['temp33'] +
                            data_process[i]['processes'][j]['metrics']['temp44'])
                if sum_temp != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'incidentScore'] = f"{round(data_process[i]['processes'][j]['metrics']['temp_all_all'] / sum_temp, 1) * 100}"
                else:
                    data_process[i]['processes'][j]['metrics']['incidentScore'] = '0'

                # Полнота inc
                if sum_temp + data_process[i]['processes'][j]['metrics']['temp55'] != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'incidentCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['processes'][j]['metrics']['temp55']), 1) * 100}"

                # Точность inc
                sum_temp = (data_process[i]['processes'][j]['metrics']['temp11_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp22_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp33_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp44_accuracy'] +
                            data_process[i]['processes'][j]['metrics']['temp55_accuracy'])
                if sum_temp != 0:
                    data_process[i]['processes'][j]['metrics'][
                        'incidentAccuracy'] = f"{round(data_process[i]['processes'][j]['metrics']['temp_all_all_accuracy'] / sum_temp, 1) * 100}"
                else:
                    data_process[i]['processes'][j]['metrics']['incidentAccuracy'] = '0'

                # Тут данные по критериям качества/inc добвляем в группу
                data_process[i]['metrics']['temp1'] += data_process[i]['processes'][j]['metrics']['temp1']
                data_process[i]['metrics']['temp2'] += data_process[i]['processes'][j]['metrics']['temp2']
                data_process[i]['metrics']['temp3'] += data_process[i]['processes'][j]['metrics']['temp3']
                data_process[i]['metrics']['temp4'] += data_process[i]['processes'][j]['metrics']['temp4']
                data_process[i]['metrics']['temp5'] += data_process[i]['processes'][j]['metrics']['temp5']
                data_process[i]['metrics']['temp_all'] += data_process[i]['processes'][j]['metrics']['temp_all']

                data_process[i]['metrics']['temp1_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp1_accuracy']
                data_process[i]['metrics']['temp2_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp2_accuracy']
                data_process[i]['metrics']['temp3_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp3_accuracy']
                data_process[i]['metrics']['temp4_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp4_accuracy']
                data_process[i]['metrics']['temp5_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp5_accuracy']
                data_process[i]['metrics']['temp_all_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp_all_accuracy']

                data_process[i]['metrics']['temp11'] += data_process[i]['processes'][j]['metrics']['temp11']
                data_process[i]['metrics']['temp22'] += data_process[i]['processes'][j]['metrics']['temp22']
                data_process[i]['metrics']['temp33'] += data_process[i]['processes'][j]['metrics']['temp33']
                data_process[i]['metrics']['temp44'] += data_process[i]['processes'][j]['metrics']['temp44']
                data_process[i]['metrics']['temp55'] += data_process[i]['processes'][j]['metrics']['temp55']
                data_process[i]['metrics']['temp_all_all'] += data_process[i]['processes'][j]['metrics']['temp_all_all']

                data_process[i]['metrics']['temp11_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp11_accuracy']
                data_process[i]['metrics']['temp22_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp22_accuracy']
                data_process[i]['metrics']['temp33_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp33_accuracy']
                data_process[i]['metrics']['temp44_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp44_accuracy']
                data_process[i]['metrics']['temp55_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp55_accuracy']
                data_process[i]['metrics']['temp_all_all_accuracy'] += data_process[i]['processes'][j]['metrics'][
                    'temp_all_all_accuracy']

            # Оценка Z в группе
            if data_process[i]['metrics']['total'] != 0 and data_process[i]['metrics']['checked'] != 0:
                data_process[i]['metrics'][
                    'checkedPercent'] = f"{round(data_process[i]['metrics']['checked'] / data_process[i]['metrics']['total'], 1) * 100}"
                data_process[i]['metrics'][
                    'completedPercent'] = f"{round(data_process[i]['metrics']['completed'] / data_process[i]['metrics']['checked'], 1) * 100}"
            else:
                data_process[i]['metrics']['checkedPercent'] = '0'
                data_process[i]['metrics']['completedPercent'] = '0'

            # теперь для группы посчитаю всего:
            data_process[i]['metrics']['temp111'] = \
                data_process[i]['metrics']['temp1'] + \
                data_process[i]['metrics']['temp11']
            data_process[i]['metrics']['temp222'] = \
                data_process[i]['metrics']['temp2'] + \
                data_process[i]['metrics']['temp22']
            data_process[i]['metrics']['temp333'] = \
                data_process[i]['metrics']['temp3'] + \
                data_process[i]['metrics']['temp33']
            data_process[i]['metrics']['temp444'] = \
                data_process[i]['metrics']['temp4'] + \
                data_process[i]['metrics']['temp44']
            data_process[i]['metrics']['temp555'] = \
                data_process[i]['metrics']['temp5'] + \
                data_process[i]['metrics']['temp55']
            data_process[i]['metrics']['temp_all_all_all'] = \
                data_process[i]['metrics']['temp_all'] + \
                data_process[i]['metrics']['temp_all_all']

            data_process[i]['metrics']['temp111_accuracy'] = \
                data_process[i]['metrics']['temp1_accuracy'] + \
                data_process[i]['metrics']['temp11_accuracy']
            data_process[i]['metrics']['temp222_accuracy'] = \
                data_process[i]['metrics']['temp2_accuracy'] + \
                data_process[i]['metrics']['temp22_accuracy']
            data_process[i]['metrics']['temp333_accuracy'] = \
                data_process[i]['metrics']['temp3_accuracy'] + \
                data_process[i]['metrics']['temp33_accuracy']
            data_process[i]['metrics']['temp444_accuracy'] = \
                data_process[i]['metrics']['temp4_accuracy'] + \
                data_process[i]['metrics']['temp44_accuracy']
            data_process[i]['metrics']['temp555_accuracy'] = \
                data_process[i]['metrics']['temp5_accuracy'] + \
                data_process[i]['metrics']['temp55_accuracy']
            data_process[i]['metrics']['temp_all_all_all_accuracy'] = \
                data_process[i]['metrics']['temp_all_accuracy'] + \
                data_process[i]['metrics']['temp_all_all_accuracy']

            data_process[i]['metrics']['totalPoints'] = data_process[i]['metrics']['temp_all_all_all']

            all_process_score['totalPoints'] += round(data_process[i]['metrics']['totalPoints'], 1)
            all_process_score['temp111'] += data_process[i]['metrics']['temp111']
            all_process_score['temp222'] += data_process[i]['metrics']['temp222']
            all_process_score['temp333'] += data_process[i]['metrics']['temp333']
            all_process_score['temp444'] += data_process[i]['metrics']['temp444']
            all_process_score['temp555'] += data_process[i]['metrics']['temp555']
            all_process_score['temp555_accuracy'] += data_process[i]['metrics']['temp555_accuracy']
            all_process_score['temp444_accuracy'] += data_process[i]['metrics']['temp444_accuracy']
            all_process_score['temp333_accuracy'] += data_process[i]['metrics']['temp333_accuracy']
            all_process_score['temp222_accuracy'] += data_process[i]['metrics']['temp222_accuracy']
            all_process_score['temp111_accuracy'] += data_process[i]['metrics']['temp111_accuracy']
            all_process_score['temp_all_all_all_accuracy'] += data_process[i]['metrics']['temp_all_all_all_accuracy']

            sum_temp = (data_process[i]['metrics']['temp111'] +
                        data_process[i]['metrics']['temp222'] +
                        data_process[i]['metrics']['temp333'] +
                        data_process[i]['metrics']['temp444'])
            if sum_temp != 0:
                data_process[i]['metrics'][
                    'totalScore'] = f"{round(data_process[i]['metrics']['temp_all_all_all'] / sum_temp, 1) * 100}"
            else:
                data_process[i]['metrics']['totalScore'] = '0'

            # Полнота
            if sum_temp + data_process[i]['metrics']['temp555'] != 0:
                data_process[i]['metrics'][
                    'totalCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['metrics']['temp555']), 1) * 100}"

            # Точность
            sum_temp = (data_process[i]['metrics']['temp111_accuracy'] +
                        data_process[i]['metrics']['temp222_accuracy'] +
                        data_process[i]['metrics']['temp333_accuracy'] +
                        data_process[i]['metrics']['temp444_accuracy'] +
                        data_process[i]['metrics']['temp555_accuracy'])
            if sum_temp != 0:
                data_process[i]['metrics'][
                    'totalAccuracy'] = f"{round(data_process[i]['metrics']['temp_all_all_all_accuracy'] / sum_temp, 1) * 100}"
            else:
                data_process[i]['metrics']['totalAccuracy'] = '0'

            # Это для критериев качества/inc(оценка) в группе
            sum_temp = (data_process[i]['metrics']['temp1'] +
                        data_process[i]['metrics']['temp2'] +
                        data_process[i]['metrics']['temp3'] +
                        data_process[i]['metrics']['temp4'])
            if sum_temp != 0:
                data_process[i]['metrics'][
                    'qualityScore'] = f"{round(data_process[i]['metrics']['temp_all'] / sum_temp, 1) * 100}"
            else:
                data_process[i]['metrics']['qualityScore'] = '0'

            # полнота
            if (sum_temp + data_process[i]['metrics']['temp5']) != 0:
                data_process[i]['metrics'][
                    'qualityCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['metrics']['temp5']), 1) * 100}"

            # Точность
            sum_temp = (data_process[i]['metrics']['temp1_accuracy'] +
                        data_process[i]['metrics']['temp2_accuracy'] +
                        data_process[i]['metrics']['temp3_accuracy'] +
                        data_process[i]['metrics']['temp4_accuracy'] +
                        data_process[i]['metrics']['temp5_accuracy'])
            if sum_temp != 0:
                data_process[i]['metrics'][
                    'qualityAccuracy'] = f"{round(data_process[i]['metrics']['temp_all_accuracy'] / sum_temp, 1) * 100}"
            else:
                data_process[i]['metrics']['qualityAccuracy'] = '0'

            # score inc
            sum_temp = (data_process[i]['metrics']['temp11'] +
                        data_process[i]['metrics']['temp22'] +
                        data_process[i]['metrics']['temp33'] +
                        data_process[i]['metrics']['temp44'])
            if sum_temp != 0:
                data_process[i]['metrics'][
                    'incidentScore'] = f"{round(data_process[i]['metrics']['temp_all_all'] / sum_temp, 1) * 100}"
            else:
                data_process[i]['metrics']['incidentScore'] = '0'

            # полнота
            if sum_temp + data_process[i]['metrics']['temp55'] != 0:
                data_process[i]['metrics'][
                    'incidentCompleteness'] = f"{round(sum_temp / (sum_temp + data_process[i]['metrics']['temp55']), 1) * 100}"

            # Точность
            sum_temp = (data_process[i]['metrics']['temp11_accuracy'] +
                        data_process[i]['metrics']['temp22_accuracy'] +
                        data_process[i]['metrics']['temp33_accuracy'] +
                        data_process[i]['metrics']['temp44_accuracy'] +
                        data_process[i]['metrics']['temp55_accuracy'])
            if sum_temp != 0:
                data_process[i]['metrics'][
                    'incidentAccuracy'] = f"{round(data_process[i]['metrics']['temp_all_all_accuracy'] / sum_temp, 1) * 100}"
            else:
                data_process[i]['metrics']['incidentAccuracy'] = '0'

        sum_temp = (all_process_score['temp111'] +
                    all_process_score['temp222'] +
                    all_process_score['temp333'] +
                    all_process_score['temp444'])
        if sum_temp != 0:
            all_process_score[
                'totalScore'] = f"{round(round(all_process_score['totalPoints'] / sum_temp, 1) * 100, 1)}"
        else:
            all_process_score['totalScore'] = '0'

        # Полнота
        if sum_temp + all_process_score['temp555'] != 0:
            all_process_score[
                'totalCompleteness'] = f"{round(round(sum_temp / (sum_temp + all_process_score['temp555']), 1) * 100, 1)}"

        # Точность
        sum_temp = (all_process_score['temp111_accuracy'] +
                    all_process_score['temp222_accuracy'] +
                    all_process_score['temp333_accuracy'] +
                    all_process_score['temp444_accuracy'] +
                    all_process_score['temp555_accuracy'])
        if sum_temp != 0:
            all_process_score[
                'totalAccuracy'] = f"{round(all_process_score['temp_all_all_all_accuracy'] / sum_temp, 1) * 100}"
        else:
            all_process_score['totalAccuracy'] = '0'

    except Exception as e:
        print(e)

    competencies_json = []
    sum_score = 0
    compl_sum = 0
    acc_sum = 0

    for i, competency in enumerate(comp_list):
        competencies_json.append({'id': i + 1, 'name': competency.name})

        if sum(dict_comp_sum[competency.name]) != 0:
            competencies_json[i][
                'score'] = f"{round((sum(dict_comp[competency.name]) / sum(dict_comp_sum[competency.name])) * 100, 1)}%"
            sum_score += (sum(dict_comp[competency.name]) / sum(dict_comp_sum[competency.name])) * 100
        else:
            competencies_json[i]['score'] = '0.0%'

        if len(dict_comp_sum[competency.name]) != 0:
            competencies_json[i][
                'completeness'] = f'{round((dict_comp_polnota[competency.name] / len(dict_comp_sum[competency.name])) * 100, 1)}%'
            compl_sum += (dict_comp_polnota[competency.name] / len(dict_comp_sum[competency.name])) * 100
        else:
            competencies_json[i]['completeness'] = '0.0%'

        if dict_comp_polnota[competency.name] != 0:
            competencies_json[i][
                'accuracy'] = f'{round((sum(dict_comp_tochnost[competency.name]) / dict_comp_polnota[competency.name]) * 100, 1)}%'
            acc_sum += (sum(dict_comp_tochnost[competency.name]) / dict_comp_polnota[competency.name]) * 100
        else:
            competencies_json[i]['accuracy'] = f'0.0%'

    processes_summary = {
        "averagePoints": round(all_process_score['totalPoints'], 1),
        "averageScore": all_process_score['totalScore'],
        "averageCompleteness": all_process_score['totalCompleteness'],
        "averageAccuracy": all_process_score['totalAccuracy'],
        "scoreClass": "high",
        "completenessClass": "medium",
        "accuracyClass": "medium"
    }

    CompetencyChecklistFilling.objects.update_or_create(
        checklist=checklist,
        filling=filling,
        defaults={'competency_json': competencies_json}
    )

    ResultsChecklistFilling.objects.update_or_create(
        filling=filling,
        defaults={'competencies_json': competencies_json,
                  'competencies_summary_json': {
                      'averageScore': f'{round(sum_score / len(competencies_json), 1)}',
                      'averageCompleteness': f'{round(compl_sum / len(competencies_json), 1)}',
                      'averageAccuracy': f'{round(acc_sum / len(competencies_json), 1)}'
                  },
                  'processes_data': data_process,
                  'processes_summary': processes_summary,
                  }
    )

def checklist_results(request, filling_id, checklist_id):
    user_role = request.user.role
    menu_items = []

    checklist = get_object_or_404(Checklist, id=checklist_id)
    if user_role == 'methodist':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    elif user_role == 'expert':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    else:
        menu_items = ROLE_MENU.get(user_role, [])

    #Тут оценка компетенций
    checklist = get_object_or_404(Checklist, id=checklist_id)
    fillings = ChecklistFilling.objects.filter(checklist=checklist, status='completed', id=filling_id).first()
    if not fillings:
        return JsonResponse({"error": "Нет завершённой оценки"}, status=400)

    results = get_object_or_404(ResultsChecklistFilling, filling=fillings)

    return render(request, 'result_checklist.html', {
        'checklist': checklist,
        'fillings': fillings,
        'menu_items': menu_items,
        'competencies_json': json.dumps(results.competencies_json),
        'competencies_summary_json': json.dumps(results.competencies_summary_json),
        'processes_data': json.dumps(results.processes_data),
        'processes_summary': json.dumps(results.processes_summary)
    })

def checklist_delete(request, checklist_id):
    checklist = get_object_or_404(Checklist, id=checklist_id)
    company = get_object_or_404(Company, id=checklist.company_id)

    checklist.delete()
    messages.success(request, "Чек-лист успешно удален.")

    return redirect('company_detail', company_id=company.id)

def checklist_filling_delete(request, filling_id, checklist_id):
    filling = get_object_or_404(ChecklistFilling, id=filling_id, checklist_id=checklist_id)

    filling.delete()
    messages.success(request, "Заполнение чек-листа успешно удалено.")

    return redirect('checklist_detail', checklist_id=checklist_id)

def checklist_filling_edit(request, filling_id, checklist_id):
    user_role = request.user.role
    menu_items = []

    checklist = get_object_or_404(Checklist, id=checklist_id)
    if user_role == 'methodist':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    elif user_role == 'expert':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    else:
        menu_items = ROLE_MENU.get(user_role, [])

    checklist = get_object_or_404(Checklist, id=checklist_id)
    filling = get_object_or_404(ChecklistFilling, id=filling_id)
    company = get_object_or_404(Company, id=checklist.company_id)
    job_title = get_object_or_404(JobTitle, id=checklist.job_title_id, company=company)

    if filling.started_at != request.user and not request.user.is_staff:
        return redirect('dashboard')


    checklist_data = checklist.data
    if isinstance(checklist_data, str):
        checklist_data = json.loads(checklist_data)

    filling_data = filling.json_data if filling.json_data else {}

    context = {
        'checklist': checklist,
        'checklist_json': json.dumps({
            'checklistId': checklist.id,
            'jobTitle': job_title.name,
            'groups': checklist_data
        }),
        'filling_json': json.dumps({
            'groups': filling_data,
            'employeeName':filling.employee,
            'fillingId': filling.id,
        }),
        'checklistId': checklist.id,
        'fillingId': filling.id,
        'companyId': company.id,
        'jobTitle': job_title.name.lower(),
        'evaluation_date': filling.started_at,
        'employee_name': filling.employee,
        'menu_items': menu_items,
    }

    return render(request, 'checklist_eva.html', context)

def delete_job_title(request, job_title_id):
    job_title = get_object_or_404(JobTitle, id=job_title_id)
    company_id = job_title.company.id  # если нужно вернуться к компании
    job_title.delete()
    return redirect('company_detail', company_id=company_id)

def competency_results(request, checklist_id):
    user_role = request.user.role
    menu_items = []

    checklist = get_object_or_404(Checklist, id=checklist_id)
    if user_role == 'methodist':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    elif user_role == 'expert':
        if checklist.company_id:
            menu_items = [{'name': 'Предприятие', 'href': f'/companies/{checklist.company_id}/'}]
    else:
        menu_items = ROLE_MENU.get(user_role, [])

    checklist = get_object_or_404(Checklist, id=checklist_id)

    competency_fillings = CompetencyChecklistFilling.objects.filter(
        checklist=checklist,
    )

    formatted_data = []
    average_competency = {}
    count = 0
    for node in competency_fillings:
        competency_list = node.competency_json

        for competency in competency_list:
            if competency['name'] in average_competency:
                average_competency[competency['name']]['score'] += float(competency['score'].strip('%'))
                average_competency[competency['name']]['completeness'] += float(competency['completeness'].strip('%'))
                average_competency[competency['name']]['accuracy'] += float(competency['accuracy'].strip('%'))
            else:
                average_competency[competency['name']] = {'score': float(competency['score'].strip('%')), 'completeness': float(competency['completeness'].strip('%')), 'accuracy': float(competency['accuracy'].strip('%'))}

        count += 1

    for key, value in average_competency.items():
        average_score = value['score'] / count
        average_completeness = value['completeness'] / count
        average_accuracy = value['accuracy'] / count
        formatted_data.append({
            'name': key,
            'averageScore': round(average_score, 1),
            'averageAccuracy': round(average_completeness, 1),
            'averageCompleteness': round(average_accuracy, 1),
            'count': count,
        })

    competency_data_json = json.dumps(formatted_data)

    return render(request, 'competency_results.html', {
        'menu_items': menu_items,
        'checklist': checklist,
        'competency_data': formatted_data,
        'competency_data_json': competency_data_json
})