"""Tests pour les commandes de management"""

import io

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase


class ManagementCommandsTest(TestCase):
    """Tests pour les commandes de management"""

    def test_setup_groups_command(self):
        """Test la commande setup_groups"""
        out = io.StringIO()
        call_command("setup_groups", stdout=out)

        # Vérifier que les groupes ont été créés
        self.assertTrue(Group.objects.filter(name="Admin").exists())
        self.assertTrue(Group.objects.filter(name="Manager").exists())
        self.assertTrue(Group.objects.filter(name="Viewer").exists())

    def test_create_admin_command(self):
        """Test la commande create_admin"""
        out = io.StringIO()
        call_command("create_admin", username="testadmin", email="test@example.com", password="testpass123", stdout=out)

        # Vérifier que l'admin a été créé
        user = User.objects.get(username="testadmin")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.email, "test@example.com")

    def test_create_demo_users_command(self):
        """Test la commande create_demo_users"""
        # Créer d'abord les groupes nécessaires
        call_command("setup_groups")

        out = io.StringIO()
        call_command("create_demo_users", stdout=out)

        # Vérifier que les utilisateurs de démonstration ont été créés
        self.assertTrue(User.objects.filter(username="superadmin").exists())
        self.assertTrue(User.objects.filter(username="manager").exists())
        self.assertTrue(User.objects.filter(username="viewer").exists())
