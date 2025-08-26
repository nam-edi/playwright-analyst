"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseNotAllowed
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
import json
import tempfile
import os
from datetime import datetime, timedelta
from django.utils.dateparse import parse_datetime
from .models import Project, Test, TestExecution, TestResult, Tag


def home(request):
    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    latest_execution = None
    latest_execution_stats = None
    
    if 'selected_project_id' in request.session:
        try:
            selected_project = Project.objects.get(id=request.session['selected_project_id'])
            # Récupérer la dernière exécution du projet
            latest_execution = selected_project.executions.first()
            
            if latest_execution:
                # Calculer les statistiques de la dernière exécution
                # Exclure les tests dont le statut attendu est "skipped"
                latest_execution_stats = {
                    'passed': latest_execution.test_results.filter(status='passed').count(),
                    'failed': latest_execution.test_results.filter(status='failed').count(),
                    'skipped': latest_execution.test_results.filter(status='skipped').exclude(expected_status='skipped').count(),
                    'flaky': latest_execution.test_results.filter(status='flaky').count(),
                    'total': latest_execution.test_results.exclude(expected_status='skipped').count(),
                }
                
        except Project.DoesNotExist:
            del request.session['selected_project_id']
    
    # Récupérer tous les projets pour la liste déroulante
    projects = Project.objects.all()
    
    context = {
        'selected_project': selected_project,
        'projects': projects,
        'latest_execution': latest_execution,
        'latest_execution_stats': latest_execution_stats,
    }
    
    return render(request, 'home.html', context)


def select_project(request):
    """Vue pour sélectionner un projet"""
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                request.session['selected_project_id'] = project.id
                messages.success(request, f'Projet "{project.name}" sélectionné')
                
                # Retourner la réponse HTMX avec redirection
                response = HttpResponse()
                response['HX-Redirect'] = request.META.get('HTTP_REFERER', '/')
                return response
                
            except Project.DoesNotExist:
                messages.error(request, 'Projet introuvable')
        else:
            # Si aucun projet sélectionné, on nettoie la session
            if 'selected_project_id' in request.session:
                del request.session['selected_project_id']
            messages.success(request, 'Aucun projet sélectionné')
            
            response = HttpResponse()
            response['HX-Redirect'] = request.META.get('HTTP_REFERER', '/')
            return response
    
    return redirect('home')


def tests_list(request):
    """Vue pour afficher la liste des tests du projet sélectionné"""
    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if 'selected_project_id' in request.session:
        try:
            selected_project = Project.objects.get(id=request.session['selected_project_id'])
        except Project.DoesNotExist:
            del request.session['selected_project_id']
    
    if not selected_project:
        messages.warning(request, 'Veuillez sélectionner un projet pour voir les tests.')
        return redirect('home')
    
    # Récupérer tous les projets pour le header
    projects = Project.objects.all()
    
    # Récupérer les TESTS du projet sélectionné (pas les résultats)
    tests = Test.objects.filter(project=selected_project).prefetch_related(
        'tags', 
        'results__execution'
    ).order_by('file_path', 'line')
    
    # Filtres basés sur les TESTS
    search = request.GET.get('search', '')
    tag_filter = request.GET.getlist('tags')
    
    if search:
        tests = tests.filter(title__icontains=search)
    
    if tag_filter:
        tests = tests.filter(tags__id__in=tag_filter).distinct()
    
    # Pagination
    paginator = Paginator(tests, 20)  # 20 tests par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Tags disponibles pour les filtres (directement depuis les tests)
    from .models import Tag
    available_tags_qs = Tag.objects.filter(test__project=selected_project).distinct()
    available_tags = [
        {'id': tag.id, 'name': tag.name, 'color': tag.color} 
        for tag in available_tags_qs
    ]
    
    context = {
        'selected_project': selected_project,
        'projects': projects,
        'page_obj': page_obj,
        'tests': page_obj,
        'available_tags': available_tags,
        'search': search,
        'tag_filter': tag_filter,
    }
    
    # Si c'est une requête HTMX, retourner seulement le contenu des tests
    if request.headers.get('HX-Request'):
        return render(request, 'cotton/tests-container.html', context)
    
    return render(request, 'tests_list.html', context)


def test_detail(request, test_id):
    """Vue pour afficher les détails d'un test dans le panneau latéral"""
    test = get_object_or_404(Test, id=test_id)
    
    # Récupérer toutes les exécutions du test, triées par date décroissante
    test_results = test.results.select_related('execution').order_by('-start_time')
    
    # Pagination pour les résultats
    paginator = Paginator(test_results, 10)  # 10 résultats par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'test': test,
        'test_results': page_obj,
        'page_obj': page_obj,
    }
    
    return render(request, 'cotton/test-detail-panel.html', context)


def update_test_comment(request, test_id):
    """Vue pour mettre à jour le commentaire d'un test via HTMX"""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    test = get_object_or_404(Test, id=test_id)
    comment = request.POST.get('comment', '').strip()
    
    test.comment = comment
    test.save()
    
    # Retourner le fragment HTML mis à jour
    context = {'test': test}
    return render(request, 'cotton/test-comment-fragment.html', context)


def htmx_example(request):
    """Exemple de vue HTMX"""
    return HttpResponse("""
        <div class="p-4 bg-green-100 border border-green-400 text-green-700 rounded">
            <h4 class="font-bold">HTMX fonctionne !</h4>
            <p>Cette réponse a été chargée dynamiquement sans rechargement de page.</p>
            <p class="text-sm mt-2">Timestamp: <span class="font-mono">{}</span></p>
        </div>
    """.format(__import__('datetime').datetime.now().strftime('%H:%M:%S')))


def executions_list(request):
    """Vue pour afficher la liste des exécutions du projet sélectionné"""
    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if 'selected_project_id' in request.session:
        try:
            selected_project = Project.objects.get(id=request.session['selected_project_id'])
        except Project.DoesNotExist:
            del request.session['selected_project_id']
    
    if not selected_project:
        messages.warning(request, 'Veuillez sélectionner un projet pour voir les exécutions.')
        return redirect('home')
    
    # Récupérer tous les projets pour le header
    projects = Project.objects.all()
    
    # Récupérer les exécutions du projet sélectionné, triées par date décroissante
    executions = TestExecution.objects.filter(project=selected_project).order_by('-start_time')
    
    # Filtres par date
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    date_preset = request.GET.get('date_preset')
    
    # Appliquer les filtres de date prédéfinis
    now = timezone.now()
    if date_preset == 'current_week':
        # Début de la semaine (lundi)
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        executions = executions.filter(start_time__gte=start_of_week)
        date_from = start_of_week.strftime('%Y-%m-%d')
        date_to = now.strftime('%Y-%m-%d')
    elif date_preset == 'current_month':
        # Début du mois
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        executions = executions.filter(start_time__gte=start_of_month)
        date_from = start_of_month.strftime('%Y-%m-%d')
        date_to = now.strftime('%Y-%m-%d')
    elif date_from or date_to:
        # Filtres de date personnalisés
        if date_from:
            try:
                date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d')
                date_from_parsed = timezone.make_aware(date_from_parsed)
                executions = executions.filter(start_time__gte=date_from_parsed)
            except ValueError:
                messages.error(request, 'Format de date de début invalide.')
                date_from = None
        
        if date_to:
            try:
                date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d')
                # Ajouter 23:59:59 pour inclure toute la journée
                date_to_parsed = date_to_parsed.replace(hour=23, minute=59, second=59)
                date_to_parsed = timezone.make_aware(date_to_parsed)
                executions = executions.filter(start_time__lte=date_to_parsed)
            except ValueError:
                messages.error(request, 'Format de date de fin invalide.')
                date_to = None
    
    # Ajouter les statistiques pour chaque exécution
    executions_with_stats = []
    for execution in executions:
        # Calculer les statistiques PASS, FAIL, SKIP (exclure les tests avec expected_status='skipped')
        test_results = TestResult.objects.filter(execution=execution)
        
        pass_count = test_results.filter(status='passed').exclude(expected_status='skipped').count()
        fail_count = test_results.filter(status__in=['failed', 'unexpected']).exclude(expected_status='skipped').count()
        skip_count = test_results.filter(status='skipped').exclude(expected_status='skipped').count()
        
        total_count = test_results.exclude(expected_status='skipped').count()
        
        executions_with_stats.append({
            'execution': execution,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'skip_count': skip_count,
            'total_count': total_count
        })
    
    # Pagination
    paginator = Paginator(executions_with_stats, 20)  # 20 exécutions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'selected_project': selected_project,
        'projects': projects,
        'page_obj': page_obj,
        'executions_with_stats': page_obj,
        'date_from': date_from,
        'date_to': date_to,
        'date_preset': date_preset,
    }
    
    return render(request, 'executions_list.html', context)


def execution_detail(request, execution_id):
    """Vue pour afficher le détail d'une exécution avec tous ses tests"""
    execution = get_object_or_404(TestExecution, id=execution_id)
    
    # Vérifier que l'exécution appartient au projet sélectionné (si défini)
    selected_project = None
    if 'selected_project_id' in request.session:
        try:
            selected_project = Project.objects.get(id=request.session['selected_project_id'])
            if execution.project != selected_project:
                messages.error(request, 'Cette exécution n\'appartient pas au projet sélectionné.')
                return redirect('executions_list')
        except Project.DoesNotExist:
            del request.session['selected_project_id']
    
    # Récupérer tous les projets pour le header
    projects = Project.objects.all()
    
    # Récupérer tous les résultats de tests pour cette exécution
    test_results = TestResult.objects.filter(execution=execution).select_related('test').prefetch_related('test__tags')
    
    # Filtres
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    tag_filter = request.GET.get('tag', '')
    sort_by = request.GET.get('sort', 'test_title')  # Par défaut tri par titre du test
    
    # Récupérer tous les tags disponibles pour cette exécution
    available_tags = Tag.objects.filter(
        test__results__execution=execution
    ).distinct().order_by('name')
    
    # Appliquer le filtre de statut
    if status_filter:
        if status_filter == 'passed':
            test_results = test_results.filter(status='passed')
        elif status_filter == 'failed':
            test_results = test_results.filter(status__in=['failed', 'unexpected'])
        elif status_filter == 'skipped':
            test_results = test_results.filter(status='skipped')
        elif status_filter == 'flaky':
            test_results = test_results.filter(status='flaky')
    
    # Appliquer le filtre de recherche
    if search:
        test_results = test_results.filter(test__title__icontains=search)
    
    # Appliquer le filtre par tag
    if tag_filter:
        test_results = test_results.filter(test__tags__name=tag_filter)
    
    # Appliquer le tri
    if sort_by == 'duration_asc':
        test_results = test_results.order_by('duration')
    elif sort_by == 'duration_desc':
        test_results = test_results.order_by('-duration')
    elif sort_by == 'status':
        test_results = test_results.order_by('status', 'test__title')
    elif sort_by == 'file_path':
        test_results = test_results.order_by('test__file_path', 'test__line')
    else:  # test_title par défaut
        test_results = test_results.order_by('test__title')
    
    # Calculer les statistiques globales (exclure les tests avec expected_status='skipped')
    all_results = TestResult.objects.filter(execution=execution)
    stats = {
        'total': all_results.exclude(expected_status='skipped').count(),
        'passed': all_results.filter(status='passed').exclude(expected_status='skipped').count(),
        'failed': all_results.filter(status__in=['failed', 'unexpected']).exclude(expected_status='skipped').count(),
        'skipped': all_results.filter(status='skipped').exclude(expected_status='skipped').count(),
        'flaky': all_results.filter(status='flaky').exclude(expected_status='skipped').count(),
    }
    
    # Pagination
    paginator = Paginator(test_results, 50)  # 50 résultats par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'execution': execution,
        'selected_project': selected_project or execution.project,
        'projects': projects,
        'page_obj': page_obj,
        'test_results': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search': search,
        'tag_filter': tag_filter,
        'sort_by': sort_by,
        'available_tags': available_tags,
    }
    
    return render(request, 'execution_detail.html', context)


def upload_json(request):
    """Vue pour afficher la page d'upload de fichiers JSON"""
    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if 'selected_project_id' in request.session:
        try:
            selected_project = Project.objects.get(id=request.session['selected_project_id'])
        except Project.DoesNotExist:
            del request.session['selected_project_id']
    
    # Récupérer tous les projets pour le header et le sélecteur
    projects = Project.objects.all()
    
    context = {
        'selected_project': selected_project,
        'projects': projects,
    }
    
    return render(request, 'upload_json.html', context)


def process_json_upload(request):
    """Vue pour traiter l'upload et l'importation d'un fichier JSON"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    # Vérifier qu'un projet est sélectionné ou fourni
    project_id = request.POST.get('project_id')
    if not project_id and 'selected_project_id' in request.session:
        project_id = request.session['selected_project_id']
    
    if not project_id:
        return JsonResponse({'error': 'Aucun projet sélectionné'}, status=400)
    
    # Vérifier que le projet existe
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Projet introuvable'}, status=404)
    
    # Vérifier qu'un fichier est fourni
    if 'json_file' not in request.FILES:
        return JsonResponse({'error': 'Aucun fichier fourni'}, status=400)
    
    uploaded_file = request.FILES['json_file']
    
    # Vérifier l'extension du fichier
    if not uploaded_file.name.endswith('.json'):
        return JsonResponse({'error': 'Le fichier doit avoir l\'extension .json'}, status=400)
    
    try:
        # Lire et parser le JSON
        file_content = uploaded_file.read().decode('utf-8')
        data = json.loads(file_content)
        
        # Traiter l'importation
        execution = import_json_data(project, data)
        
        return JsonResponse({
            'success': True,
            'message': f'Importation réussie ! Exécution créée : {execution.start_time.strftime("%d/%m/%Y à %H:%M")}',
            'execution_id': execution.id,
            'redirect_url': f'/execution/{execution.id}/'
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Fichier JSON invalide : {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erreur lors de l\'importation : {str(e)}'}, status=500)


def import_json_data(project, data):
    """Fonction pour importer les données JSON (basée sur la commande Django)"""
    
    # Créer l'exécution de test
    execution = create_test_execution(project, data)
    
    # Traiter les suites et tests
    for suite in data.get('suites', []):
        process_suite(suite, execution)
    
    return execution


def create_test_execution(project, data):
    """Crée une exécution de test à partir des données JSON"""
    config = data.get('config', {})
    metadata = config.get('metadata', {})
    git_commit = metadata.get('gitCommit', {})
    ci = metadata.get('ci', {})
    stats = data.get('stats', {})

    # Convertir les timestamps
    start_time = parse_datetime(stats.get('startTime'))
    if not start_time:
        start_time = datetime.now()

    execution = TestExecution.objects.create(
        project=project,
        config_file=config.get('configFile', ''),
        root_dir=config.get('rootDir', ''),
        playwright_version=config.get('version', ''),
        workers=config.get('workers', 1),
        actual_workers=metadata.get('actualWorkers', 1),
        git_commit_hash=git_commit.get('hash', ''),
        git_commit_short_hash=git_commit.get('shortHash', ''),
        git_branch=git_commit.get('branch', ''),
        git_commit_subject=git_commit.get('subject', ''),
        git_author_name=git_commit.get('author', {}).get('name', ''),
        git_author_email=git_commit.get('author', {}).get('email', ''),
        ci_build_href=ci.get('buildHref', ''),
        ci_commit_href=ci.get('commitHref', ''),
        start_time=start_time,
        duration=stats.get('duration', 0),
        expected_tests=stats.get('expected', 0),
        skipped_tests=stats.get('skipped', 0),
        unexpected_tests=stats.get('unexpected', 0),
        flaky_tests=stats.get('flaky', 0),
        raw_json=data
    )

    return execution


def process_suite(suite, execution, parent_tags=None):
    """Traite une suite de tests"""
    if parent_tags is None:
        parent_tags = []
    
    # Récupérer les tags de cette suite s'il y en a
    suite_tags = parent_tags.copy()
    if 'tags' in suite:
        suite_tags.extend(suite.get('tags', []))

    # Traiter les specs de cette suite
    for spec in suite.get('specs', []):
        process_spec(spec, execution, suite.get('file', ''), suite_tags)

    # Traiter les sous-suites
    for sub_suite in suite.get('suites', []):
        process_suite(sub_suite, execution, suite_tags)


def process_spec(spec, execution, file_path, parent_tags=None):
    """Traite un spec (test)"""
    if parent_tags is None:
        parent_tags = []
        
    # Récupérer tous les tags (parent + spec)
    all_tags = parent_tags.copy()
    all_tags.extend(spec.get('tags', []))
    
    # Créer ou récupérer le test
    spec_test_id = spec.get('id', '')  # ID du spec
    title = spec.get('title', '')
    line = spec.get('line', 0)
    column = spec.get('column', 0)
    
    # Extraire le test_id des annotations des tests enfants
    annotation_test_id = ''
    story = ''
    
    # Chercher dans les tests enfants pour récupérer les annotations
    for test_data in spec.get('tests', []):
        for annotation in test_data.get('annotations', []):
            if annotation.get('type') == 'id':
                annotation_test_id = annotation.get('description', '')
            elif annotation.get('type') == 'story':
                story = annotation.get('description', '')
    
    # Priorité au test_id des annotations, sinon utiliser l'ID du spec
    test_id = annotation_test_id or spec_test_id
    
    test = None
    created = False
    
    try:
        # Stratégie 1: Si test_id fourni, chercher d'abord par test_id
        if test_id:
            try:
                test = Test.objects.get(project=execution.project, test_id=test_id)
                # Test trouvé par test_id, mettre à jour les autres champs si nécessaire
                updated = False
                if test.title != title:
                    test.title = title
                    updated = True
                if test.file_path != file_path:
                    test.file_path = file_path
                    updated = True
                if test.line != line:
                    test.line = line
                    updated = True
                if test.column != column:
                    test.column = column
                    updated = True
                if story and test.story != story:
                    test.story = story
                    updated = True
                
                if updated:
                    test.save()
                    
            except Test.DoesNotExist:
                # Pas trouvé par test_id, chercher par caractéristiques uniques
                try:
                    test = Test.objects.get(
                        project=execution.project,
                        title=title,
                        file_path=file_path,
                        line=line,
                        column=column
                    )
                    # Test trouvé par caractéristiques, vérifier si on peut ajouter le test_id
                    if not test.test_id:
                        # Vérifier que ce test_id n'est pas déjà pris
                        existing_test_with_id = Test.objects.filter(
                            project=execution.project, 
                            test_id=test_id
                        ).first()
                        
                        if not existing_test_with_id:
                            test.test_id = test_id
                            if story:
                                test.story = story
                            test.save()
                    else:
                        # Le test a déjà un test_id différent, mettre à jour story si nécessaire
                        if story and test.story != story:
                            test.story = story
                            test.save()
                        
                except Test.DoesNotExist:
                    # Vérifier d'abord que ce test_id n'est pas déjà pris avant de créer
                    existing_test_with_id = Test.objects.filter(
                        project=execution.project, 
                        test_id=test_id
                    ).first()
                    
                    if existing_test_with_id:
                        # test_id déjà pris, créer sans test_id pour éviter le conflit
                        test = Test.objects.create(
                            project=execution.project,
                            title=title,
                            file_path=file_path,
                            line=line,
                            column=column,
                            test_id='',  # Laisser vide pour éviter le conflit
                            story=story
                        )
                    else:
                        # test_id libre, créer avec
                        test = Test.objects.create(
                            project=execution.project,
                            title=title,
                            file_path=file_path,
                            line=line,
                            column=column,
                            test_id=test_id,
                            story=story
                        )
                    created = True
        else:
            # Pas de test_id, utiliser get_or_create sur les caractéristiques uniques
            test, created = Test.objects.get_or_create(
                project=execution.project,
                title=title,
                file_path=file_path,
                line=line,
                column=column,
                defaults={
                    'test_id': '',
                    'story': story
                }
            )
            
    except Exception as e:
        # En cas d'erreur, essayer de récupérer par caractéristiques uniques
        try:
            test = Test.objects.get(
                project=execution.project,
                title=title,
                file_path=file_path,
                line=line,
                column=column
            )
        except Test.DoesNotExist:
            # Si vraiment rien ne fonctionne, créer sans test_id pour éviter les conflits
            try:
                test = Test.objects.create(
                    project=execution.project,
                    title=title,
                    file_path=file_path,
                    line=line,
                    column=column,
                    test_id='',  # Créer sans test_id pour éviter les conflits
                    story=story
                )
                created = True
            except:
                # Dernière tentative: récupérer n'importe quel test correspondant
                test = Test.objects.filter(
                    project=execution.project,
                    title=title,
                    file_path=file_path,
                    line=line,
                    column=column
                ).first()
                if not test:
                    raise e

    # Ajouter tous les tags au test
    for tag_name in all_tags:
        if tag_name:  # Éviter les tags vides
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'color': '#3b82f6'}
            )
            test.tags.add(tag)

    for test_data in spec.get('tests', []):
        process_test_result(test_data, test, execution)


def process_test_result(test_data, test, execution):
    """Traite un résultat de test avec gestion intelligente des retries"""
    # Le test_id et story sont maintenant gérés dans process_spec
    # Ici on ne fait que traiter les résultats
    
    # Analyser tous les résultats pour déterminer la stratégie de retry
    results = test_data.get('results', [])
    if not results:
        return

    # Séparer les résultats par retry
    results_by_retry = {}
    final_status = None
    
    for result in results:
        retry_num = result.get('retry', 0)
        status = result.get('status', '')
        
        if retry_num not in results_by_retry:
            results_by_retry[retry_num] = []
        results_by_retry[retry_num].append(result)
        
        # Le status final est celui du retry le plus élevé
        if final_status is None or retry_num > max([r.get('retry', 0) for r in results if r != result]):
            final_status = status

    # Déterminer quel résultat garder selon la règle :
    # - Si final PASS : garder le dernier retry (celui qui a réussi)
    # - Si final FAIL : garder le premier retry (l'échec initial)
    
    if final_status in ['passed', 'expected']:
        # Test finalement passé : garder le dernier retry
        max_retry = max(results_by_retry.keys())
        selected_result = results_by_retry[max_retry][0]  # Premier résultat du retry max
    else:
        # Test finalement échoué : garder le premier retry
        min_retry = min(results_by_retry.keys())
        selected_result = results_by_retry[min_retry][0]  # Premier résultat du retry min

    # Créer le TestResult avec le résultat sélectionné
    start_time = parse_datetime(selected_result.get('startTime'))
    if not start_time:
        start_time = execution.start_time

    # Vérifier si un résultat existe déjà pour ce test et cette exécution
    existing_result = TestResult.objects.filter(
        execution=execution,
        test=test
    ).first()
    
    if existing_result:
        # Mettre à jour le résultat existant
        existing_result.project_id = test_data.get('projectId', '')
        existing_result.project_name = test_data.get('projectName', '')
        existing_result.timeout = test_data.get('timeout', 0)
        existing_result.expected_status = test_data.get('expectedStatus', '')
        existing_result.status = selected_result.get('status', '')
        existing_result.worker_index = selected_result.get('workerIndex', 0)
        existing_result.parallel_index = selected_result.get('parallelIndex', 0)
        existing_result.duration = selected_result.get('duration', 0)
        existing_result.retry = selected_result.get('retry', 0)
        existing_result.start_time = start_time
        existing_result.errors = selected_result.get('errors', [])
        existing_result.stdout = selected_result.get('stdout', [])
        existing_result.stderr = selected_result.get('stderr', [])
        existing_result.steps = selected_result.get('steps', [])
        existing_result.annotations = selected_result.get('annotations', [])
        existing_result.attachments = selected_result.get('attachments', [])
        existing_result.save()
    else:
        # Créer un nouveau résultat
        TestResult.objects.create(
            execution=execution,
            test=test,
            project_id=test_data.get('projectId', ''),
            project_name=test_data.get('projectName', ''),
            timeout=test_data.get('timeout', 0),
            expected_status=test_data.get('expectedStatus', ''),
            status=selected_result.get('status', ''),
            worker_index=selected_result.get('workerIndex', 0),
            parallel_index=selected_result.get('parallelIndex', 0),
            duration=selected_result.get('duration', 0),
            retry=selected_result.get('retry', 0),
            start_time=start_time,
            errors=selected_result.get('errors', []),
            stdout=selected_result.get('stdout', []),
            stderr=selected_result.get('stderr', []),
            steps=selected_result.get('steps', []),
            annotations=selected_result.get('annotations', []),
            attachments=selected_result.get('attachments', [])
        )


def fetch_from_ci(request, project_id):
    """Vue pour récupérer automatiquement les résultats depuis la CI"""
    from .services.ci_services import fetch_latest_test_results, fetch_test_results_by_job_id, CIServiceError
    
    project = get_object_or_404(Project, id=project_id)
    
    if not project.has_ci_configuration():
        messages.error(request, "Ce projet n'a pas de configuration CI.")
        return redirect('upload_json')
    
    if request.method == 'GET':
        # Afficher le formulaire de sélection
        context = {
            'project': project,
            'ci_provider': project.get_ci_provider(),
            'ci_config': project.get_ci_config_details()
        }
        return render(request, 'fetch_from_ci.html', context)
    
    elif request.method == 'POST':
        branch = request.POST.get('branch', 'main')
        job_id = request.POST.get('job_id', '').strip()
        
        try:
            if job_id:
                # Récupérer depuis un job spécifique
                json_data = fetch_test_results_by_job_id(project, job_id)
                source_info = f"Job ID: {job_id}"
            else:
                # Récupérer le dernier job réussi
                json_data = fetch_latest_test_results(project, branch)
                source_info = f"Dernier job réussi sur '{branch}'"
            
            if not json_data:
                messages.error(request, "Aucun résultat trouvé.")
                return redirect('fetch_from_ci', project_id=project_id)
            
            # Importer les données JSON
            execution = import_json_data(project, json_data)
            
            messages.success(
                request, 
                f"Résultats importés avec succès depuis la CI ({source_info}). "
                f"Exécution créée: {execution}"
            )
            
            return redirect('execution_detail', execution_id=execution.id)
            
        except CIServiceError as e:
            messages.error(request, f"Erreur CI: {e}")
            return redirect('fetch_from_ci', project_id=project_id)
        except Exception as e:
            messages.error(request, f"Erreur lors de l'import: {e}")
            return redirect('fetch_from_ci', project_id=project_id)
    
    return HttpResponseNotAllowed(['GET', 'POST'])


def ci_status_check(request, project_id):
    """Vue AJAX pour vérifier le statut de la configuration CI"""
    from .services.ci_services import get_ci_service, CIServiceError
    
    project = get_object_or_404(Project, id=project_id)
    
    if not project.has_ci_configuration():
        return JsonResponse({
            'status': 'error',
            'message': 'Aucune configuration CI trouvée'
        })
    
    try:
        ci_service = get_ci_service(project)
        if not ci_service:
            return JsonResponse({
                'status': 'error',
                'message': 'Service CI non disponible'
            })
        
        # Tester la connexion en récupérant le dernier job
        branch = request.GET.get('branch', 'main')
        latest_job_id = ci_service.get_latest_successful_job_id(branch)
        
        if latest_job_id:
            return JsonResponse({
                'status': 'success',
                'message': f'Connexion réussie. Dernier job: {latest_job_id}',
                'latest_job_id': latest_job_id,
                'branch': branch
            })
        else:
            return JsonResponse({
                'status': 'warning',
                'message': f'Connexion réussie mais aucun job trouvé sur la branche "{branch}"'
            })
            
    except CIServiceError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erreur de connexion: {e}'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erreur inattendue: {e}'
        })