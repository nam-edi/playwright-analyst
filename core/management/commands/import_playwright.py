"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from core.models import Project, Tag, TestExecution, Test, TestResult


class Command(BaseCommand):
    help = 'Importe un fichier JSON de résultats Playwright dans un projet'

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=int, help='ID du projet')
        parser.add_argument('json_file', type=str, help='Chemin vers le fichier JSON')
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Nom d\'utilisateur (par défaut: admin)'
        )

    def handle(self, *args, **options):
        project_id = options['project_id']
        json_file = options['json_file']
        username = options['user']

        # Vérifier que le fichier existe
        if not os.path.exists(json_file):
            raise CommandError(f'Le fichier {json_file} n\'existe pas.')

        # Récupérer le projet
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise CommandError(f'Le projet avec l\'ID {project_id} n\'existe pas.')

        # Récupérer l'utilisateur
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'L\'utilisateur {username} n\'existe pas.')

        # Charger le JSON
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Erreur lors de la lecture du JSON: {e}')

        self.stdout.write(self.style.SUCCESS(f'Importation des données pour le projet: {project.name}'))

        # Créer l'exécution de test
        execution = self.create_test_execution(project, data)
        self.stdout.write(f'Exécution créée: {execution}')

        # Traiter les suites et tests
        test_count = 0
        result_count = 0

        for suite in data.get('suites', []):
            test_count_suite, result_count_suite = self.process_suite(suite, execution)
            test_count += test_count_suite
            result_count += result_count_suite

        self.stdout.write(self.style.SUCCESS(
            f'Importation terminée: {test_count} tests, {result_count} résultats'
        ))

    def create_test_execution(self, project, data):
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

    def process_suite(self, suite, execution, parent_tags=None):
        """Traite une suite de tests"""
        if parent_tags is None:
            parent_tags = []
        
        # Récupérer les tags de cette suite s'il y en a
        suite_tags = parent_tags.copy()
        if 'tags' in suite:
            suite_tags.extend(suite.get('tags', []))
        
        test_count = 0
        result_count = 0

        # Traiter les specs de cette suite
        for spec in suite.get('specs', []):
            test_count_spec, result_count_spec = self.process_spec(spec, execution, suite.get('file', ''), suite_tags)
            test_count += test_count_spec
            result_count += result_count_spec

        # Traiter les sous-suites
        for sub_suite in suite.get('suites', []):
            test_count_suite, result_count_suite = self.process_suite(sub_suite, execution, suite_tags)
            test_count += test_count_suite
            result_count += result_count_suite

        return test_count, result_count

    def process_spec(self, spec, execution, file_path, parent_tags=None):
        """Traite un spec (test)"""
        if parent_tags is None:
            parent_tags = []
            
        # Récupérer tous les tags (parent + spec)
        all_tags = parent_tags.copy()
        all_tags.extend(spec.get('tags', []))
        
        # Créer ou récupérer le test basé sur test_id
        test_id = spec.get('id', '')
        title = spec.get('title', '')
        line = spec.get('line', 0)
        column = spec.get('column', 0)
        
        # Chercher d'abord par test_id s'il existe
        test = None
        created = False
        
        if test_id:
            try:
                test = Test.objects.get(project=execution.project, test_id=test_id)
                # Mettre à jour les champs si nécessaire
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
                
                if updated:
                    test.save()
                    self.stdout.write(f'Test mis à jour: {test.title}')
                    
            except Test.DoesNotExist:
                # Le test n'existe pas, on le crée
                test = Test.objects.create(
                    project=execution.project,
                    title=title,
                    file_path=file_path,
                    line=line,
                    column=column,
                    test_id=test_id,
                    story=''
                )
                created = True
        else:
            # Pas de test_id, on utilise l'ancienne logique
            test, created = Test.objects.get_or_create(
                project=execution.project,
                title=title,
                file_path=file_path,
                line=line,
                column=column,
                defaults={
                    'test_id': '',
                    'story': ''
                }
            )

        if created:
            self.stdout.write(f'Nouveau test créé: {test.title}')

        # Ajouter tous les tags au test
        for tag_name in all_tags:
            if tag_name:  # Éviter les tags vides
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'color': '#3b82f6'}
                )
                test.tags.add(tag)
                if created:
                    self.stdout.write(f'Nouveau tag créé: {tag_name}')

        test_count = 1
        result_count = 0

        for test_data in spec.get('tests', []):
            result_count += self.process_test_result(test_data, test, execution)

        return test_count, result_count

    def process_test_result(self, test_data, test, execution):
        """Traite un résultat de test"""
        # Traiter les annotations pour récupérer story et test_id
        for annotation in test_data.get('annotations', []):
            if annotation.get('type') == 'story':
                test.story = annotation.get('description', '')
            elif annotation.get('type') == 'id':
                test.test_id = annotation.get('description', '')

        test.save()

        # Créer les résultats pour chaque exécution
        result_count = 0
        for result in test_data.get('results', []):
            start_time = parse_datetime(result.get('startTime'))
            if not start_time:
                start_time = execution.start_time

            TestResult.objects.create(
                execution=execution,
                test=test,
                project_id=test_data.get('projectId', ''),
                project_name=test_data.get('projectName', ''),
                timeout=test_data.get('timeout', 0),
                expected_status=test_data.get('expectedStatus', ''),
                status=result.get('status', ''),
                worker_index=result.get('workerIndex', 0),
                parallel_index=result.get('parallelIndex', 0),
                duration=result.get('duration', 0),
                retry=result.get('retry', 0),
                start_time=start_time,
                errors=result.get('errors', []),
                stdout=result.get('stdout', []),
                stderr=result.get('stderr', []),
                steps=result.get('steps', []),
                annotations=result.get('annotations', []),
                attachments=result.get('attachments', [])
            )
            result_count += 1

        return result_count