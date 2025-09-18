from django import template

register = template.Library()


@register.filter
def get_status_config(status):
    """Get status configuration for display"""
    status_configs = {
        "passed": {
            "label": "Passé",
            "color": "#10b981",
            "icon": '<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>',
        },
        "failed": {
            "label": "Échoué",
            "color": "#ef4444",
            "icon": '<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>',
        },
        "skipped": {
            "label": "Ignoré",
            "color": "#6b7280",
            "icon": '<path fill-rule="evenodd" d="M3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"></path>',
        },
        "flaky": {
            "label": "Instable",
            "color": "#f59e0b",
            "icon": '<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>',
        },
        "timedOut": {
            "label": "Timeout",
            "color": "#dc2626",
            "icon": '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path>',
        },
        "interrupted": {
            "label": "Interrompu",
            "color": "#7c3aed",
            "icon": '<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"></path>',
        },
    }

    return status_configs.get(
        status,
        {
            "label": status.title(),
            "color": "#6b7280",
            "icon": '<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>',
        },
    )


@register.filter
def duration_format(duration_ms):
    """Format duration from milliseconds to human readable format"""
    if not duration_ms:
        return "0ms"

    duration_ms = int(duration_ms)

    if duration_ms < 1000:
        return f"{duration_ms}ms"

    seconds = duration_ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}min"

    hours = minutes / 60
    return f"{hours:.1f}h"


@register.filter
def duration_detailed(duration_ms):
    """Format duration from milliseconds to detailed format (Xmin Ys Zms)"""
    if not duration_ms:
        return "0ms"

    duration_ms = int(duration_ms)

    if duration_ms < 1000:
        return f"{duration_ms}ms"

    # Calculer les minutes, secondes et millisecondes
    minutes = duration_ms // 60000  # 60 * 1000 ms
    remaining_ms = duration_ms % 60000
    seconds = remaining_ms // 1000
    milliseconds = remaining_ms % 1000

    parts = []

    if minutes > 0:
        parts.append(f"{minutes}min")

    if seconds > 0:
        parts.append(f"{seconds}s")

    if milliseconds > 0 or not parts:  # Afficher les ms si c'est la seule unité ou s'il y en a
        parts.append(f"{milliseconds}ms")

    return " ".join(parts)


@register.filter
def percentage(value, total):
    """Calculate percentage"""
    if not total or total == 0:
        return 0
    return round((value / total) * 100, 1)


@register.filter
def split(value, separator):
    """Split a string by separator"""
    if value:
        return value.split(separator)
    return []


@register.filter
def average_duration_last_passed(test):
    """Calculate average duration of last 5 passed test executions"""
    if not test:
        return None

    # Récupérer les 5 derniers résultats avec status='passed'
    passed_results = test.results.filter(status="passed").order_by("-start_time")[:5]

    if not passed_results:
        return None

    # Calculer la durée moyenne
    total_duration = sum(result.duration for result in passed_results)
    average = total_duration / len(passed_results)

    return average


@register.filter
def linebreaks_simple(value):
    """Convert line breaks to HTML <br> tags"""
    if not value:
        return ""

    # Remplace les différents types de retour à la ligne par <br>
    import re

    # Gère \r\n (Windows), \n (Unix/Linux/Mac), \r (Mac classique)
    value = re.sub(r"\r\n|\r|\n", "<br>", str(value))
    return value


@register.filter
def gte(value, arg):
    """Greater than or equal comparison filter"""
    try:
        return float(value) >= float(arg)
    except (ValueError, TypeError):
        return False


@register.filter
def is_success_rate_90_or_more(pass_count, total_count):
    """Check if success rate is 90% or more"""
    if not total_count or total_count == 0:
        return False
    return (pass_count * 10) >= (total_count * 9)


@register.filter
def visible_tags(test):
    """Get only the visible tags (not excluded) for a test"""
    if not test or not hasattr(test, "project") or not test.project:
        return test.tags.all() if test and hasattr(test, "tags") else []

    # Filtrer les tags exclus du projet
    excluded_tag_ids = test.project.excluded_tags.values_list("id", flat=True)
    return test.tags.exclude(id__in=excluded_tag_ids)
