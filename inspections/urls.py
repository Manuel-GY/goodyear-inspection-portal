from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('logo-goodyear.png', views.logo_view, name='logo_view'),
    path('api/admin-status/', views.api_admin_status, name='api_admin_status'),
    path('api/ldap-login/', views.api_ldap_login, name='api_ldap_login'),
    path('api/ldap-logout/', views.api_ldap_logout, name='api_ldap_logout'),
    path('api/drawer-structure/', views.api_drawer_structure, name='api_drawer_structure'),
    path('api/carts/', views.api_carts_list_create, name='api_carts_list_create'),
    path('api/carts/<str:cart_id>/', views.api_cart_detail_update_delete, name='api_cart_detail_update_delete'),
    path('api/carts/<str:cart_id>/drawers/<int:drawer_num>/tools/', views.api_cart_drawer_tools, name='api_cart_drawer_tools'),
    path('api/inspections/', views.api_inspections_list_create, name='api_inspections_list_create'),
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/reset-factory/', views.api_reset_factory, name='api_reset_factory'),
    path('api/download-excel-template/', views.api_download_excel_template, name='api_download_excel_template'),
    path('api/import-excel/', views.api_import_excel, name='api_import_excel'),
]
