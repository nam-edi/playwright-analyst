"""
Vues pour la gestion des erreurs personnalisées
"""

from django.shortcuts import render


def custom_404_view(request, exception):
    """Vue personnalisée pour l'erreur 404"""
    return render(request, "404.html", status=404)


def custom_500_view(request):
    """Vue personnalisée pour l'erreur 500"""
    return render(request, "500.html", status=500)
