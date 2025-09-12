"""
Commande de management pour optimiser et nettoyer les données PW Analyst
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Q
from django.utils import timezone

from core.models import Project, Test, TestExecution, TestResult

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Optimise et nettoie les données de PW Analyst"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les actions sans les exécuter",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Nombre de jours à conserver pour les données anciennes (défaut: 90)",
        )
        parser.add_argument(
            "--clean-orphans",
            action="store_true",
            help="Nettoie les enregistrements orphelins",
        )
        parser.add_argument(
            "--recalculate-stats",
            action="store_true",
            help="Recalcule toutes les statistiques",
        )
        parser.add_argument(
            "--optimize-tags",
            action="store_true",
            help="Optimise les tags inutilisés",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.days_to_keep = options["days"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("Mode DRY RUN - Aucune modification ne sera effectuée"))

        # Statistiques initiales
        self.show_initial_stats()

        if options["clean_orphans"]:
            self.clean_orphaned_records()

        if options["recalculate_stats"]:
            self.recalculate_statistics()

        if options["optimize_tags"]:
            self.optimize_tags()

        # Nettoyer les vieilles données
        self.clean_old_data()

        # Statistiques finales
        self.show_final_stats()

        self.stdout.write(self.style.SUCCESS("Optimisation terminée avec succès!"))

    def show_initial_stats(self):
        """Affiche les statistiques initiales"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.HTTP_INFO("STATISTIQUES INITIALES"))
        self.stdout.write("=" * 50)

        total_projects = Project.objects.count()
        total_executions = TestExecution.objects.count()
        total_tests = Test.objects.count()
        total_results = TestResult.objects.count()

        self.stdout.write(f"Projets: {total_projects}")
        self.stdout.write(f"Exécutions: {total_executions}")
        self.stdout.write(f"Tests: {total_tests}")
        self.stdout.write(f"Résultats de tests: {total_results}")

        # Statistiques par statut
        status_stats = TestResult.objects.values("status").annotate(count=Count("id")).order_by("-count")

        self.stdout.write("\nRépartition par statut:")
        for stat in status_stats:
            self.stdout.write(f"  {stat['status']}: {stat['count']}")

    def clean_orphaned_records(self):
        """Nettoie les enregistrements orphelins"""
        self.stdout.write("\n" + "-" * 50)
        self.stdout.write(self.style.HTTP_INFO("NETTOYAGE DES ENREGISTREMENTS ORPHELINS"))
        self.stdout.write("-" * 50)

        # Résultats de tests sans test ou exécution
        orphaned_results = TestResult.objects.filter(Q(test__isnull=True) | Q(execution__isnull=True))
        orphaned_count = orphaned_results.count()

        if orphaned_count > 0:
            self.stdout.write(f"Résultats orphelins trouvés: {orphaned_count}")
            if not self.dry_run:
                deleted_count = orphaned_results.delete()[0]
                self.stdout.write(self.style.SUCCESS(f"✓ {deleted_count} résultats orphelins supprimés"))
        else:
            self.stdout.write("✓ Aucun résultat orphelin trouvé")

        # Tests sans résultats depuis longtemps
        cutoff_date = timezone.now() - timedelta(days=self.days_to_keep * 2)
        unused_tests = Test.objects.annotate(result_count=Count("results")).filter(
            Q(result_count=0) & Q(created_at__lt=cutoff_date)
        )
        unused_count = unused_tests.count()

        if unused_count > 0:
            self.stdout.write(f"Tests inutilisés trouvés: {unused_count}")
            if not self.dry_run:
                deleted_count = unused_tests.delete()[0]
                self.stdout.write(self.style.SUCCESS(f"✓ {deleted_count} tests inutilisés supprimés"))
        else:
            self.stdout.write("✓ Aucun test inutilisé trouvé")

    def recalculate_statistics(self):
        """Recalcule toutes les statistiques"""
        self.stdout.write("\n" + "-" * 50)
        self.stdout.write(self.style.HTTP_INFO("RECALCUL DES STATISTIQUES"))
        self.stdout.write("-" * 50)

        executions = TestExecution.objects.all()
        updated_count = 0

        for execution in executions:
            if not self.dry_run:
                # Recalculer total_tests
                execution.total_tests = execution.test_results.count()

                # Recalculer success_rate
                total = execution.total_tests
                if total > 0:
                    passed = execution.test_results.filter(status="passed").count()
                    execution.success_rate = (passed / total) * 100
                else:
                    execution.success_rate = 0

                execution.save()
                updated_count += 1

        if self.dry_run:
            self.stdout.write(f"Exécutions à mettre à jour: {executions.count()}")
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ {updated_count} exécutions mises à jour"))

    def optimize_tags(self):
        """Optimise les tags inutilisés"""
        self.stdout.write("\n" + "-" * 50)
        self.stdout.write(self.style.HTTP_INFO("OPTIMISATION DES TAGS"))
        self.stdout.write("-" * 50)

        from core.models import Tag

        # Trouver les tags inutilisés
        unused_tags = Tag.objects.annotate(test_count=Count("test")).filter(test_count=0)

        unused_count = unused_tags.count()

        if unused_count > 0:
            self.stdout.write(f"Tags inutilisés trouvés: {unused_count}")
            if not self.dry_run:
                deleted_count = unused_tags.delete()[0]
                self.stdout.write(self.style.SUCCESS(f"✓ {deleted_count} tags inutilisés supprimés"))
        else:
            self.stdout.write("✓ Aucun tag inutilisé trouvé")

        # Statistiques des tags
        tag_stats = Tag.objects.annotate(test_count=Count("test")).order_by("-test_count")[:10]

        self.stdout.write("\nTop 10 des tags les plus utilisés:")
        for tag in tag_stats:
            self.stdout.write(f"  {tag.name}: {tag.test_count} tests")

    def clean_old_data(self):
        """Nettoie les anciennes données"""
        self.stdout.write("\n" + "-" * 50)
        self.stdout.write(self.style.HTTP_INFO("NETTOYAGE DES ANCIENNES DONNÉES"))
        self.stdout.write("-" * 50)

        cutoff_date = timezone.now() - timedelta(days=self.days_to_keep)

        # Anciennes exécutions
        old_executions = TestExecution.objects.filter(start_time__lt=cutoff_date)
        old_count = old_executions.count()

        if old_count > 0:
            self.stdout.write(f"Exécutions anciennes (>{self.days_to_keep} jours): {old_count}")
            if not self.dry_run:
                # Les résultats seront supprimés en cascade
                deleted_count = old_executions.delete()[0]
                self.stdout.write(self.style.SUCCESS(f"✓ {deleted_count} anciennes exécutions supprimées"))
        else:
            self.stdout.write(f"✓ Aucune exécution ancienne (>{self.days_to_keep} jours)")

    def show_final_stats(self):
        """Affiche les statistiques finales"""
        if self.dry_run:
            return

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.HTTP_INFO("STATISTIQUES FINALES"))
        self.stdout.write("=" * 50)

        total_projects = Project.objects.count()
        total_executions = TestExecution.objects.count()
        total_tests = Test.objects.count()
        total_results = TestResult.objects.count()

        self.stdout.write(f"Projets: {total_projects}")
        self.stdout.write(f"Exécutions: {total_executions}")
        self.stdout.write(f"Tests: {total_tests}")
        self.stdout.write(f"Résultats de tests: {total_results}")

        # Recommandations
        self.stdout.write("\n" + self.style.HTTP_INFO("RECOMMANDATIONS:"))

        if total_results > 100000:
            self.stdout.write(
                self.style.WARNING("⚠️  Nombre élevé de résultats de tests. " "Considérez réduire la période de rétention.")
            )

        if total_tests > 10000:
            self.stdout.write(self.style.WARNING("⚠️  Nombre élevé de tests. " "Vérifiez les tests obsolètes."))

        avg_success_rate = TestExecution.objects.aggregate(avg=Avg("success_rate"))["avg"]

        if avg_success_rate and avg_success_rate < 80:
            self.stdout.write(
                self.style.ERROR(f"⚠️  Taux de réussite moyen bas: {avg_success_rate:.1f}%. " "Vérifiez la qualité des tests.")
            )
        elif avg_success_rate:
            self.stdout.write(self.style.SUCCESS(f"✓ Taux de réussite moyen: {avg_success_rate:.1f}%"))
