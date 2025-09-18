"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

import json
import os
from datetime import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.utils.dateparse import parse_datetime

from projects.models import Project
from testing.models import Tag, Test, TestExecution, TestResult


class Command(BaseCommand):
    help = "Importe un fichier JSON de résultats Playwright dans un projet"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int, help="ID du projet")
        parser.add_argument("json_file", type=str, help="Chemin vers le fichier JSON")
        parser.add_argument("--user", type=str, default="admin", help="Nom d'utilisateur (par défaut: admin)")

    def handle(self, *args, **options):
        project_id = options["project_id"]
        json_file = options["json_file"]
        username = options["user"]

        # Vérifier que le fichier existe
        if not os.path.exists(json_file):
            raise CommandError(f"Le fichier {json_file} n'existe pas.")

        # Récupérer le projet
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise CommandError(f"Le projet avec l'ID {project_id} n'existe pas.")

        # Récupérer l'utilisateur
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"L'utilisateur {username} n'existe pas.")

        # Charger le JSON
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Erreur lors de la lecture du JSON: {e}")

        self.stdout.write(self.style.SUCCESS(f"Importation des données pour le projet: {project.name}"))

        # Créer l'exécution de test
        execution = self.create_test_execution(project, data)
        self.stdout.write(f"Exécution créée: {execution}")

        # Traiter les suites et tests
        test_count = 0
        result_count = 0

        for suite in data.get("suites", []):
            test_count_suite, result_count_suite = self.process_suite(suite, execution)
            test_count += test_count_suite
            result_count += result_count_suite

        self.stdout.write(self.style.SUCCESS(f"Importation terminée: {test_count} tests, {result_count} résultats"))

    def create_test_execution(self, project, data):
        """Crée une exécution de test à partir des données JSON"""
        config = data.get("config", {})
        metadata = config.get("metadata", {})
        git_commit = metadata.get("gitCommit", {})
        ci = metadata.get("ci", {})
        stats = data.get("stats", {})

        # Vérifier que ci est bien un dictionnaire, sinon utiliser un dict vide
        if not isinstance(ci, dict):
            ci = {}

        # Vérifier que git_commit est bien un dictionnaire
        if not isinstance(git_commit, dict):
            git_commit = {}

        # Vérifier que author est bien un dictionnaire
        author = git_commit.get("author", {})
        if not isinstance(author, dict):
            author = {}

        # Convertir les timestamps
        start_time = parse_datetime(stats.get("startTime"))
        if not start_time:
            start_time = datetime.now()

        # Récupérer les liens CI directement depuis les métadonnées
        ci_build_href = metadata.get("buildHref", "")
        ci_commit_href = ci.get("commitHref", "")

        execution = TestExecution.objects.create(
            project=project,
            config_file=config.get("configFile", ""),
            root_dir=config.get("rootDir", ""),
            playwright_version=config.get("version", ""),
            workers=config.get("workers", 1),
            actual_workers=metadata.get("actualWorkers", 1),
            git_commit_hash=git_commit.get("hash", ""),
            git_commit_short_hash=git_commit.get("shortHash", ""),
            git_branch=git_commit.get("branch", ""),  # Récupérer la branche depuis gitCommit
            git_commit_subject=git_commit.get("subject", ""),
            git_author_name=author.get("name", ""),
            git_author_email=author.get("email", ""),
            ci_build_href=ci_build_href,
            ci_commit_href=ci_commit_href,
            start_time=start_time,
            duration=stats.get("duration", 0),
            expected_tests=stats.get("expected", 0),
            skipped_tests=stats.get("skipped", 0),
            unexpected_tests=stats.get("unexpected", 0),
            flaky_tests=stats.get("flaky", 0),
            raw_json=data,
        )

        return execution

    def process_suite(self, suite, execution, parent_tags=None):
        """Traite une suite de tests"""
        if parent_tags is None:
            parent_tags = []

        # Récupérer les tags de cette suite s'il y en a
        suite_tags = parent_tags.copy()
        if "tags" in suite:
            suite_tags.extend(suite.get("tags", []))

        test_count = 0
        result_count = 0

        # Traiter les specs de cette suite
        for spec in suite.get("specs", []):
            test_count_spec, result_count_spec = self.process_spec(spec, execution, suite.get("file", ""), suite_tags)
            test_count += test_count_spec
            result_count += result_count_spec

        # Traiter les sous-suites
        for sub_suite in suite.get("suites", []):
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
        all_tags.extend(spec.get("tags", []))

        # Créer ou récupérer le test basé sur test_id
        title = spec.get("title", "")
        line = spec.get("line", 0)
        column = spec.get("column", 0)

        # Récupérer le test_id depuis les annotations des tests (pas depuis le spec)
        test_id = ""
        for test_data in spec.get("tests", []):
            for annotation in test_data.get("annotations", []):
                if annotation.get("type") == "id":
                    test_id = annotation.get("description", "").strip()
                    break
            if test_id:  # Si on a trouvé un test_id, on s'arrête
                break

        # Logique claire selon vos critères
        test = None
        created = False

        if test_id:
            # Si test_id présent, recherche UNIQUEMENT par test_id
            try:
                test = Test.objects.get(project=execution.project, test_id=test_id)
                self.stdout.write(f"Test trouvé par test_id '{test_id}': {test.title}")
            except Test.DoesNotExist:
                # Aucun test avec ce test_id, on va créer un nouveau test
                test = None
        else:
            # Si pas de test_id, recherche par project + title + file_path
            try:
                test = Test.objects.get(project=execution.project, title=title, file_path=file_path)
                self.stdout.write(f"Test trouvé par title + file_path: {test.title} ({file_path})")
            except Test.DoesNotExist:
                # Aucun test avec ces caractéristiques, on va créer un nouveau test
                test = None
            except Test.MultipleObjectsReturned:
                # Plusieurs tests avec le même title + file_path mais ligne/colonne différentes
                # Prendre le premier par ordre d'ID
                test = Test.objects.filter(project=execution.project, title=title, file_path=file_path).first()
                self.stdout.write(f"Plusieurs tests trouvés, utilisation du premier: {test.title} (ID: {test.id})")

        if test is None:
            # Créer un nouveau test
            try:
                test = Test.objects.create(
                    project=execution.project,
                    title=title,
                    file_path=file_path,
                    line=line,
                    column=column,
                    test_id=test_id if test_id else "",
                    story="",
                )
                created = True
                self.stdout.write(f"Nouveau test créé: {test.title}")
            except IntegrityError as e:
                # Gestion des conflits lors de la création
                if "unique_test_id_per_project" in str(e) and test_id:
                    # Conflit sur test_id - ne devrait pas arriver car on a vérifié avant
                    self.stdout.write(f"Erreur: test_id '{test_id}' existe déjà: {e}")
                    raise e
                elif "unique_together" in str(e) or "UNIQUE constraint failed" in str(e):
                    # Conflit sur les caractéristiques uniques (project, title, file_path, line, column)
                    # Cela peut arriver si on cherche par (project, title, file_path) mais qu'un test
                    # avec les mêmes (project, title, file_path, line, column) existe déjà
                    try:
                        # Essayer de récupérer le test existant avec toutes les caractéristiques
                        test = Test.objects.get(
                            project=execution.project, title=title, file_path=file_path, line=line, column=column
                        )
                        created = False
                        self.stdout.write(f"Test existant récupéré après conflit: {test.title}")
                    except Test.DoesNotExist:
                        # Très rare, mais peut arriver en cas de concurrence
                        self.stdout.write(f"Conflit de création non résolu: {e}")
                        raise e
                else:
                    raise e
        else:
            # Test existant trouvé, mettre à jour les champs
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

            # Pour les tests trouvés par caractéristiques (sans test_id), on peut assigner le test_id du JSON
            if not test_id:
                # Si le JSON n'a pas de test_id, on s'assure que le test n'en a pas non plus
                if test.test_id != "":
                    test.test_id = ""
                    updated = True
            else:
                # Si le JSON a un test_id, on l'assigne au test (seulement si différent)
                if test.test_id != test_id:
                    test.test_id = test_id
                    updated = True

            # Sauvegarder si des champs ont été mis à jour
            if updated:
                try:
                    test.save()
                    self.stdout.write(f"Test mis à jour: {test.title}")
                except IntegrityError as e:
                    self.stdout.write(f"Erreur lors de la mise à jour du test '{test.title}': {e}")
                    raise e

        # Ajouter tous les tags au test
        for tag_name in all_tags:
            if tag_name:  # Éviter les tags vides
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    project=execution.project,
                    defaults={"color": Tag.get_next_available_color(execution.project)},
                )
                test.tags.add(tag)
                if created:
                    self.stdout.write(f"Nouveau tag créé: {tag_name} avec couleur {tag.color}")

        test_count = 1
        result_count = 0

        for test_data in spec.get("tests", []):
            result_count += self.process_test_result(test_data, test, execution)

        return test_count, result_count

    def process_test_result(self, test_data, test, execution):
        """Traite un résultat de test"""
        # Traiter les annotations pour récupérer story et test_id
        test_updated = False
        new_test_id = None

        for annotation in test_data.get("annotations", []):
            if annotation.get("type") == "story":
                if test.story != annotation.get("description", ""):
                    test.story = annotation.get("description", "")
                    test_updated = True
            elif annotation.get("type") == "id":
                new_test_id = annotation.get("description", "")

        # Gérer la mise à jour du test_id avec vérification de conflit
        if new_test_id and test.test_id != new_test_id:
            # Vérifier si ce test_id est déjà utilisé par un autre test
            existing_with_test_id = (
                Test.objects.filter(project=execution.project, test_id=new_test_id).exclude(id=test.id).first()
            )

            if existing_with_test_id is None:
                # Aucun autre test n'a ce test_id, on peut l'assigner
                test.test_id = new_test_id
                test_updated = True
            else:
                # Un autre test a déjà ce test_id, on garde l'ancien
                self.stdout.write(
                    f"Test_id '{new_test_id}' déjà utilisé par un autre test, "
                    f"conservation de '{test.test_id}' pour: {test.title}"
                )

        # Sauvegarder seulement si nécessaire
        if test_updated:
            try:
                test.save()
            except IntegrityError as e:
                self.stdout.write(f"Erreur lors de la sauvegarde du test {test.title}: {e}")
                # Ne pas lever l'erreur, continuer avec l'ancien test

        # Créer un seul résultat par test, en utilisant le dernier retry
        results = test_data.get("results", [])
        if results:
            # Trier les résultats par retry pour avoir le dernier en premier
            sorted_results = sorted(results, key=lambda r: r.get("retry", 0), reverse=True)
            last_result = sorted_results[0]  # Le dernier retry
            first_result = sorted_results[-1]  # Le premier essai

            # Utiliser le premier essai pour le start_time et certaines infos de base
            start_time = parse_datetime(first_result.get("startTime"))
            if not start_time:
                start_time = execution.start_time

            # Calculer la durée totale (somme de tous les retries)
            total_duration = sum(result.get("duration", 0) for result in results)

            # Agréger les erreurs, stdout, stderr de tous les retries
            all_errors = []
            all_stdout = []
            all_stderr = []
            all_steps = []
            all_attachments = []

            for result in results:
                all_errors.extend(result.get("errors", []))
                all_stdout.extend(result.get("stdout", []))
                all_stderr.extend(result.get("stderr", []))
                all_steps.extend(result.get("steps", []))
                all_attachments.extend(result.get("attachments", []))

            # Créer un seul TestResult avec le statut du dernier retry
            TestResult.objects.create(
                execution=execution,
                test=test,
                project_id=test_data.get("projectId", ""),
                project_name=test_data.get("projectName", ""),
                timeout=test_data.get("timeout", 0),
                expected_status=test_data.get("expectedStatus", ""),
                status=last_result.get("status", ""),  # Statut du dernier retry
                worker_index=last_result.get("workerIndex", 0),
                parallel_index=last_result.get("parallelIndex", 0),
                duration=total_duration,  # Durée totale de tous les retries
                retry=last_result.get("retry", 0),  # Nombre total de retries
                start_time=start_time,  # Heure de début du premier essai
                errors=all_errors,  # Toutes les erreurs
                stdout=all_stdout,  # Tous les stdout
                stderr=all_stderr,  # Tous les stderr
                steps=all_steps,  # Toutes les étapes
                annotations=last_result.get("annotations", []),  # Annotations du dernier retry
                attachments=all_attachments,  # Tous les attachments
            )
            result_count = 1
        else:
            result_count = 0

        return result_count

    def try_build_ci_link(self, metadata, git_commit):
        """Essaie de construire automatiquement le lien CI basé sur les métadonnées"""
        import os

        # Variables d'environnement courantes pour différentes CI
        # GitLab CI
        if os.getenv("GITLAB_CI"):
            project_url = os.getenv("CI_PROJECT_URL")
            pipeline_id = os.getenv("CI_PIPELINE_ID")
            job_id = os.getenv("CI_JOB_ID")
            if all([project_url, pipeline_id]):
                if job_id:
                    return f"{project_url}/-/jobs/{job_id}"
                else:
                    return f"{project_url}/-/pipelines/{pipeline_id}"

        # GitHub Actions
        elif os.getenv("GITHUB_ACTIONS"):
            server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
            repository = os.getenv("GITHUB_REPOSITORY")
            run_id = os.getenv("GITHUB_RUN_ID")
            if all([repository, run_id]):
                return f"{server_url}/{repository}/actions/runs/{run_id}"

        # Jenkins
        elif os.getenv("JENKINS_URL"):
            build_url = os.getenv("BUILD_URL")
            if build_url:
                return build_url

        # Azure DevOps
        elif os.getenv("AZURE_HTTP_USER_AGENT"):
            system_team_foundation_collection_uri = os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI")
            system_team_project = os.getenv("SYSTEM_TEAMPROJECT")
            build_id = os.getenv("BUILD_BUILDID")
            if all([system_team_foundation_collection_uri, system_team_project, build_id]):
                return f"{system_team_foundation_collection_uri.rstrip('/')}/{system_team_project}/_build/results?buildId={build_id}"

        # Si aucune CI détectée, essayer de construire à partir des métadonnées du commit
        commit_hash = git_commit.get("hash", "")
        environment = metadata.get("environment", "")

        # Si on a un environment qui ressemble à un nom de build/deployment
        if environment and commit_hash:
            # Format générique basé sur l'environnement
            return f"#ci-build-{environment}-{commit_hash[:8]}"

        return ""

    def try_build_commit_link(self, metadata, git_commit):
        """Essaie de construire automatiquement le lien vers le commit"""
        import os

        commit_hash = git_commit.get("hash", "")
        if not commit_hash:
            return ""

        # GitLab CI
        if os.getenv("GITLAB_CI"):
            project_url = os.getenv("CI_PROJECT_URL")
            if project_url:
                return f"{project_url}/-/commit/{commit_hash}"

        # GitHub Actions
        elif os.getenv("GITHUB_ACTIONS"):
            server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
            repository = os.getenv("GITHUB_REPOSITORY")
            if repository:
                return f"{server_url}/{repository}/commit/{commit_hash}"

        # Si aucune CI détectée mais qu'on peut deviner depuis l'email ou autre métadonnée
        author_email = git_commit.get("author", {}).get("email", "")

        # Essayer de deviner le provider depuis l'email ou les métadonnées
        if "gitlab" in author_email.lower():
            # Cas générique GitLab - difficile sans plus d'infos
            pass
        elif "github" in author_email.lower():
            # Cas générique GitHub - difficile sans plus d'infos
            pass

        return ""
