from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import login_view, dashboard, edit_roles, users_list, user_edit, user_delete, user_create, company_list, \
    company_detail, company_create, company_edit, company_delete, create_checklist, \
    save_all, save_assessments, load_default_assessments, checklist_detail, evaluate_checklist, submit_evaluation, \
    checklist_results, checklist_filling_delete, checklist_filling_edit, checklist_delete, delete_job_title, \
    competency_results

urlpatterns = [
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('users/', users_list, name='users_list'),
    path('users/create/', user_create, name='user_create'),
    path('users/edit/<int:user_id>/', user_edit, name='user_edit'),
    path('users/delete/<int:user_id>/', user_delete, name='user_delete'),

    path('companies/', company_list, name='company_list'),
    path('companies/<int:company_id>/', company_detail, name='company_detail'),
    path('companies/create/', company_create, name='company_create'),
    path('companies/<int:company_id>/edit/', company_edit, name='company_edit'),
    path('companies/<int:company_id>/delete/', company_delete, name='company_delete'),
    path('company/<int:company_id>/edit_roles/', edit_roles, name='edit_roles'),


    path('checklist/create/<int:company_id>/<int:job_title_id>/', create_checklist, name='create_checklist'),
    path('save_all/', save_all, name='save_all'),

    path('company/<int:company_id>/save-assessments/', save_assessments, name='save_assessments'),
    path('company/<int:company_id>/load-default-assessments/', load_default_assessments, name='load_default_assessments'),

    path('checklist/<int:checklist_id>/', checklist_detail, name='checklist_detail'),
    path('checklist/<int:checklist_id>/evaluate/', evaluate_checklist, name='evaluate_checklist'),
    path('submit-evaluation/', submit_evaluation, name='submit_evaluation'),
    path('checklist/<int:checklist_id>/filling/<int:filling_id>/results/', checklist_results, name='checklist_results'),
    path('checklist/<int:checklist_id>/filling/<int:filling_id>/delete/', checklist_filling_delete, name='checklist_filling_delete'),
    path('checklist/<int:checklist_id>/filling/<int:filling_id>/edit/', checklist_filling_edit, name='checklist_filling_edit'),
    path('checklist/<int:checklist_id>/filling/<int:filling_id>/edit/', checklist_filling_edit, name='checklist_filling_edit'),
    path('checklist/<int:checklist_id>/delete/', checklist_delete, name='checklist_delete'),

    path('job_title/<int:job_title_id>/delete/', delete_job_title, name='delete_job_title'),
    path('checklist/<int:checklist_id>/competency-results/', competency_results, name='competency_results'),

]
