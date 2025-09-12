"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.core.exceptions import ValidationError
from django.db import models


class Tag(models.Model):
    """Tags pour catégoriser les tests"""

    name = models.CharField(max_length=100, verbose_name="Nom du tag")
    color = models.CharField(max_length=7, default="#3b82f6", verbose_name="Couleur")  # Hex color
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="tags", verbose_name="Projet")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["project__name", "name"]
        unique_together = [
            ["name", "project"],  # Un tag est unique par projet
            ["color", "project"],  # Une couleur est unique par projet
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["color", "project"],
                name="unique_color_per_project",
                violation_error_message="Cette couleur est déjà utilisée pour un autre tag de ce projet.",
            )
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    def clean(self):
        """Validation personnalisée pour empêcher la duplication de couleurs par projet"""
        super().clean()
        if self.project_id and self.color:
            # Vérifier si un autre tag du même projet utilise déjà cette couleur
            existing_tags = Tag.objects.filter(project=self.project, color=self.color).exclude(pk=self.pk)

        if existing_tags.exists():
            existing_tag = existing_tags.first()
            raise ValidationError(
                {
                    "color": f'La couleur {self.color} est déjà utilisée par le tag "{existing_tag.name}" de ce projet. Veuillez choisir une autre couleur.'
                }
            )

    def save(self, *args, **kwargs):
        """Appeler clean() avant de sauvegarder"""
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def get_next_available_color(project):
        """
        Retourne la prochaine couleur disponible pour un projet donné.
        Utilise les couleurs prédéfinies du widget ColorPicker en priorité.
        """
        # Couleurs prédéfinies du widget (dans l'ordre de priorité)
        predefined_colors = [
            # Bleus
            "#1e3a8a",
            "#1e40af",
            "#2563eb",
            "#3b82f6",
            "#60a5fa",
            "#93c5fd",
            "#dbeafe",
            "#0ea5e9",
            "#0284c7",
            "#0369a1",
            # Verts
            "#14532d",
            "#166534",
            "#15803d",
            "#16a34a",
            "#22c55e",
            "#4ade80",
            "#bbf7d0",
            "#10b981",
            "#059669",
            "#047857",
            # Rouges
            "#7f1d1d",
            "#991b1b",
            "#dc2626",
            "#ef4444",
            "#f87171",
            "#fca5a5",
            "#fecaca",
            "#e11d48",
            "#be123c",
            "#9f1239",
            # Oranges
            "#9a3412",
            "#c2410c",
            "#ea580c",
            "#f97316",
            "#fb923c",
            "#fdba74",
            "#fed7aa",
            "#f59e0b",
            "#d97706",
            "#b45309",
            # Violets
            "#581c87",
            "#6b21a8",
            "#7c3aed",
            "#8b5cf6",
            "#a78bfa",
            "#c4b5fd",
            "#e9d5ff",
            "#a855f7",
            "#9333ea",
            "#7e22ce",
            # Roses
            "#831843",
            "#9d174d",
            "#be185d",
            "#db2777",
            "#ec4899",
            "#f472b6",
            "#f9a8d4",
            "#e879f9",
            "#d946ef",
            "#c026d3",
            # Jaunes
            "#92400e",
            "#a16207",
            "#ca8a04",
            "#eab308",
            "#facc15",
            "#fde047",
            "#fef08a",
            "#f59e0b",
            "#d97706",
            "#b45309",
            # Cyans
            "#164e63",
            "#155e75",
            "#0891b2",
            "#0e7490",
            "#06b6d4",
            "#22d3ee",
            "#67e8f9",
            "#a7f3d0",
            "#6ee7b7",
            "#34d399",
            # Gris
            "#111827",
            "#1f2937",
            "#374151",
            "#4b5563",
            "#6b7280",
            "#9ca3af",
            "#d1d5db",
            "#e5e7eb",
            "#f3f4f6",
            "#f9fafb",
            # Spéciaux
            "#fbbf24",
            "#f472b6",
            "#34d399",
            "#60a5fa",
            "#a78bfa",
            "#fb7185",
            "#fbbf24",
            "#10b981",
            "#3b82f6",
            "#8b5cf6",
        ]

        # Obtenir les couleurs déjà utilisées dans ce projet
        used_colors = set(Tag.objects.filter(project=project).values_list("color", flat=True))

        # Trouver la première couleur prédéfinie disponible
        for color in predefined_colors:
            if color not in used_colors:
                return color

        # Si toutes les couleurs prédéfinies sont utilisées, générer une couleur aléatoire
        import random

        while True:
            new_color = f"#{random.randint(0, 16777215):06x}"
            if new_color not in used_colors:
                return new_color


class TestExecution(models.Model):
    """Exécution complète de tests (correspond à un JSON de résultats)"""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="executions", verbose_name="Projet")

    # Données de configuration
    config_file = models.CharField(max_length=500, blank=True, verbose_name="Fichier de configuration")
    root_dir = models.CharField(max_length=500, blank=True, verbose_name="Répertoire racine")
    playwright_version = models.CharField(max_length=50, blank=True, verbose_name="Version Playwright")
    workers = models.IntegerField(default=1, verbose_name="Nombre de workers")
    actual_workers = models.IntegerField(default=1, verbose_name="Workers réels")

    # Métadonnées Git
    git_commit_hash = models.CharField(max_length=40, blank=True, verbose_name="Hash du commit")
    git_commit_short_hash = models.CharField(max_length=10, blank=True, verbose_name="Hash court du commit")
    git_branch = models.CharField(max_length=200, blank=True, verbose_name="Branche Git")
    git_commit_subject = models.TextField(blank=True, verbose_name="Sujet du commit")
    git_author_name = models.CharField(max_length=200, blank=True, verbose_name="Auteur")
    git_author_email = models.EmailField(blank=True, verbose_name="Email auteur")

    # Métadonnées CI
    ci_build_href = models.URLField(blank=True, verbose_name="Lien vers le build CI")
    ci_commit_href = models.URLField(blank=True, verbose_name="Lien vers le commit CI")

    # Statistiques d'exécution
    start_time = models.DateTimeField(verbose_name="Début d'exécution")
    duration = models.FloatField(verbose_name="Durée (ms)")
    expected_tests = models.IntegerField(default=0, verbose_name="Tests attendus")
    skipped_tests = models.IntegerField(default=0, verbose_name="Tests ignorés")
    unexpected_tests = models.IntegerField(default=0, verbose_name="Tests inattendus")
    flaky_tests = models.IntegerField(default=0, verbose_name="Tests instables")

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Importé le")
    comment = models.TextField(blank=True, verbose_name="Commentaire")
    raw_json = models.JSONField(verbose_name="JSON brut", help_text="Données JSON complètes")

    class Meta:
        verbose_name = "Exécution de tests"
        verbose_name_plural = "Exécutions de tests"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.project.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def total_tests(self):
        return self.expected_tests + self.skipped_tests + self.unexpected_tests + self.flaky_tests

    @property
    def success_rate(self):
        if self.total_tests == 0:
            return 0
        return (self.expected_tests / self.total_tests) * 100


class Test(models.Model):
    """Test unique (peut être exécuté plusieurs fois)"""

    title = models.CharField(max_length=500, verbose_name="Titre du test")
    file_path = models.CharField(max_length=500, verbose_name="Chemin du fichier")
    line = models.IntegerField(verbose_name="Ligne")
    column = models.IntegerField(verbose_name="Colonne")

    # Annotations
    test_id = models.CharField(max_length=100, blank=True, verbose_name="ID du test")
    story = models.TextField(blank=True, verbose_name="Histoire/Description")
    comment = models.TextField(blank=True, verbose_name="Commentaire")

    # Relations
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="tests", verbose_name="Projet")
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Tags")

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Tests"
        unique_together = ["project", "title", "file_path", "line", "column"]
        ordering = ["file_path", "line"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "test_id"],
                condition=models.Q(test_id__isnull=False) & ~models.Q(test_id=""),
                name="unique_test_id_per_project",
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.file_path}:{self.line})"

    def get_latest_result(self):
        """Retourne le dernier résultat d'exécution de ce test"""
        return self.results.order_by("-start_time").first()

    def get_latest_status(self):
        """Retourne le statut du dernier résultat d'exécution"""
        latest = self.get_latest_result()
        return latest.status if latest else None

    def get_success_rate(self):
        """Calcule le taux de réussite de ce test"""
        total = self.results.count()
        if total == 0:
            return 0
        passed = self.results.filter(status="passed").count()
        return (passed / total) * 100


class TestResult(models.Model):
    """Résultat d'exécution d'un test spécifique"""

    STATUS_CHOICES = [
        ("passed", "Passé"),
        ("failed", "Échoué"),
        ("skipped", "Ignoré"),
        ("flaky", "Instable"),
        ("expected", "Attendu"),
        ("unexpected", "Inattendu"),
    ]

    execution = models.ForeignKey(
        TestExecution, on_delete=models.CASCADE, related_name="test_results", verbose_name="Exécution"
    )
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="results", verbose_name="Test")

    # Informations sur l'exécution
    project_id = models.CharField(max_length=50, verbose_name="ID projet Playwright")
    project_name = models.CharField(max_length=200, verbose_name="Nom projet Playwright")
    timeout = models.IntegerField(verbose_name="Timeout (ms)")
    expected_status = models.CharField(max_length=20, verbose_name="Statut attendu")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Statut")

    # Résultats d'exécution
    worker_index = models.IntegerField(verbose_name="Index du worker")
    parallel_index = models.IntegerField(verbose_name="Index parallèle")
    duration = models.FloatField(verbose_name="Durée (ms)")
    retry = models.IntegerField(default=0, verbose_name="Tentative")
    start_time = models.DateTimeField(verbose_name="Début")

    # Données brutes
    errors = models.JSONField(default=list, verbose_name="Erreurs")
    stdout = models.JSONField(default=list, verbose_name="Sortie standard")
    stderr = models.JSONField(default=list, verbose_name="Sortie d'erreur")
    steps = models.JSONField(default=list, verbose_name="Étapes")
    annotations = models.JSONField(default=list, verbose_name="Annotations")
    attachments = models.JSONField(default=list, verbose_name="Pièces jointes")

    class Meta:
        verbose_name = "Résultat de test"
        verbose_name_plural = "Résultats de tests"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.test.title} - {self.status} ({self.duration}ms)"

    @property
    def has_errors(self):
        return len(self.errors) > 0

    @property
    def duration_seconds(self):
        return self.duration / 1000
