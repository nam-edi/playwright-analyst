"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/

Services pour récupérer les artifacts depuis les CI (GitLab et GitHub)
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import requests


class CIServiceError(Exception):
    """Exception levée lors d'erreurs avec les services CI"""


class BaseCIService(ABC):
    """Service de base pour les intégrations CI"""

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def fetch_artifact_json(self, job_id: str) -> Dict[Any, Any]:
        """
        Récupère le JSON depuis les artifacts du job spécifié

        Args:
            job_id: Identifiant du job/run

        Returns:
            Dict contenant les données JSON récupérées

        Raises:
            CIServiceError: En cas d'erreur lors de la récupération
        """

    @abstractmethod
    def get_latest_successful_job_id(self, branch: str = "main") -> Optional[str]:
        """
        Récupère l'ID du dernier job réussi pour une branche donnée

        Args:
            branch: Nom de la branche (par défaut "main")

        Returns:
            ID du job ou None si aucun job trouvé
        """


class GitLabCIService(BaseCIService):
    """Service pour GitLab CI/CD"""

    def __init__(self, gitlab_config):
        super().__init__(gitlab_config)
        self.base_url = gitlab_config.gitlab_url.rstrip("/")
        self.project_id = gitlab_config.project_id
        self.access_token = gitlab_config.access_token
        self.job_name = gitlab_config.job_name
        self.artifact_path = gitlab_config.artifact_path

        self.headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    def fetch_artifact_json(self, job_id: str) -> Dict[Any, Any]:
        """Récupère le JSON depuis les artifacts GitLab"""
        try:
            # URL pour télécharger l'artifact
            artifact_url = (
                f"{self.base_url}/api/v4/projects/{self.project_id}/" f"jobs/{job_id}/artifacts/{self.artifact_path}"
            )

            response = requests.get(artifact_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Vérifier le type de contenu
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type.lower():
                raise CIServiceError(f"Le contenu de l'artifact n'est pas du JSON (type: {content_type})")

            # Vérifier que la réponse n'est pas vide
            if not response.content:
                raise CIServiceError("L'artifact est vide")

            json_data = response.json()

            # Vérifier que c'est bien un dictionnaire
            if not isinstance(json_data, dict):
                raise CIServiceError(f"L'artifact JSON n'est pas un objet valide (type: {type(json_data)})")

            return json_data

        except requests.exceptions.RequestException as e:
            raise CIServiceError(f"Erreur lors de la récupération de l'artifact GitLab: {e}")
        except json.JSONDecodeError as e:
            raise CIServiceError(f"Erreur lors du parsing JSON: {e}")
        except CIServiceError:
            # Re-lever les erreurs CIServiceError sans les modifier
            raise
        except Exception as e:
            raise CIServiceError(f"Erreur inattendue lors de la récupération de l'artifact: {e}")

    def get_latest_successful_job_id(self, branch: str = "main") -> Optional[str]:
        """Récupère l'ID du dernier job GitLab réussi"""
        try:
            # Récupérer les pipelines de la branche
            pipelines_url = (
                f"{self.base_url}/api/v4/projects/{self.project_id}/pipelines"
                f"?ref={branch}&status=success&order_by=updated_at&sort=desc"
            )

            response = requests.get(pipelines_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            pipelines = response.json()

            if not pipelines:
                return None

            # Pour chaque pipeline récent, chercher le job spécifié
            for pipeline in pipelines[:5]:  # Limite aux 5 derniers pipelines
                jobs_url = f"{self.base_url}/api/v4/projects/{self.project_id}/" f"pipelines/{pipeline['id']}/jobs"

                jobs_response = requests.get(jobs_url, headers=self.headers, timeout=30)
                jobs_response.raise_for_status()
                jobs = jobs_response.json()

                # Chercher le job avec le bon nom et status success
                for job in jobs:
                    if job["name"] == self.job_name and job["status"] == "success":
                        return str(job["id"])

            return None

        except requests.exceptions.RequestException as e:
            raise CIServiceError(f"Erreur lors de la recherche du job GitLab: {e}")


class GitHubCIService(BaseCIService):
    """Service pour GitHub Actions"""

    def __init__(self, github_config):
        super().__init__(github_config)
        self.repository = github_config.repository
        self.access_token = github_config.access_token
        self.workflow_name = github_config.workflow_name
        self.artifact_name = github_config.artifact_name
        self.json_filename = github_config.json_filename

        self.headers = {"Authorization": f"token {self.access_token}", "Accept": "application/vnd.github.v3+json"}

    def fetch_artifact_json(self, run_id: str) -> Dict[Any, Any]:
        """Récupère le JSON depuis les artifacts GitHub Actions"""
        try:
            # 1. Récupérer la liste des artifacts du run
            artifacts_url = f"https://api.github.com/repos/{self.repository}/" f"actions/runs/{run_id}/artifacts"

            response = requests.get(artifacts_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            artifacts_data = response.json()

            # 2. Trouver l'artifact avec le bon nom
            target_artifact = None
            for artifact in artifacts_data["artifacts"]:
                if artifact["name"] == self.artifact_name:
                    target_artifact = artifact
                    break

            if not target_artifact:
                raise CIServiceError(f"Artifact '{self.artifact_name}' non trouvé")

            # 3. Télécharger l'artifact (ZIP)
            download_url = target_artifact["archive_download_url"]
            download_response = requests.get(download_url, headers=self.headers, timeout=30)
            download_response.raise_for_status()

            # 4. Extraire le JSON depuis le ZIP
            import io
            import zipfile

            with zipfile.ZipFile(io.BytesIO(download_response.content)) as zip_file:
                if self.json_filename not in zip_file.namelist():
                    raise CIServiceError(f"Fichier '{self.json_filename}' non trouvé dans l'artifact")

                with zip_file.open(self.json_filename) as json_file:
                    json_data = json.load(json_file)

                    # Vérifier que c'est bien un dictionnaire
                    if not isinstance(json_data, dict):
                        raise CIServiceError(f"L'artifact JSON n'est pas un objet valide (type: {type(json_data)})")

                    return json_data

        except requests.exceptions.RequestException as e:
            raise CIServiceError(f"Erreur lors de la récupération de l'artifact GitHub: {e}")
        except json.JSONDecodeError as e:
            raise CIServiceError(f"Erreur lors du parsing JSON: {e}")
        except zipfile.BadZipFile as e:
            raise CIServiceError(f"Erreur lors de l'extraction du ZIP: {e}")
        except CIServiceError:
            # Re-lever les erreurs CIServiceError sans les modifier
            raise
        except Exception as e:
            raise CIServiceError(f"Erreur inattendue lors de la récupération de l'artifact: {e}")

    def get_latest_successful_job_id(self, branch: str = "main") -> Optional[str]:
        """Récupère l'ID du dernier run GitHub Actions réussi"""
        try:
            # Récupérer les workflow runs
            runs_url = (
                f"https://api.github.com/repos/{self.repository}/actions/runs"
                f"?branch={branch}&status=completed&conclusion=success&per_page=10"
            )

            response = requests.get(runs_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            runs_data = response.json()

            # Filtrer par nom de workflow
            for run in runs_data["workflow_runs"]:
                if run["name"] == self.workflow_name:
                    return str(run["id"])

            return None

        except requests.exceptions.RequestException as e:
            raise CIServiceError(f"Erreur lors de la recherche du run GitHub: {e}")


def get_ci_service(project) -> Optional[BaseCIService]:
    """
    Factory pour créer le bon service CI selon la configuration du projet

    Args:
        project: Instance du modèle Project

    Returns:
        Instance du service CI approprié ou None si pas de configuration
    """
    if not project.has_ci_configuration():
        return None

    provider = project.get_ci_provider()
    config_details = project.get_ci_config_details()

    if provider == "gitlab":
        return GitLabCIService(config_details)
    elif provider == "github":
        return GitHubCIService(config_details)

    return None


def fetch_latest_test_results(project, branch: str = "main") -> Optional[Dict[Any, Any]]:
    """
    Récupère les derniers résultats de tests depuis la CI configurée

    Args:
        project: Instance du modèle Project
        branch: Branche à analyser (par défaut "main")

    Returns:
        Dict contenant les résultats JSON ou None si impossible

    Raises:
        CIServiceError: En cas d'erreur lors de la récupération
    """
    ci_service = get_ci_service(project)
    if not ci_service:
        return None

    # Récupérer l'ID du dernier job réussi
    job_id = ci_service.get_latest_successful_job_id(branch)
    if not job_id:
        raise CIServiceError(f"Aucun job réussi trouvé sur la branche '{branch}'")

    # Récupérer les résultats JSON
    return ci_service.fetch_artifact_json(job_id)


def fetch_test_results_by_job_id(project, job_id: str) -> Dict[Any, Any]:
    """
    Récupère les résultats de tests pour un job/run spécifique

    Args:
        project: Instance du modèle Project
        job_id: ID du job/run

    Returns:
        Dict contenant les résultats JSON

    Raises:
        CIServiceError: En cas d'erreur lors de la récupération
    """
    ci_service = get_ci_service(project)
    if not ci_service:
        raise CIServiceError("Aucune configuration CI trouvée pour ce projet")

    return ci_service.fetch_artifact_json(job_id)
