from django import template

register = template.Library()

@register.filter
def has_group(user, group_name):
    """
    Retourne le nom du premier groupe du user, ou une chaîne vide si aucun groupe.
    """
    return user.groups.filter(name=group_name).exists()
