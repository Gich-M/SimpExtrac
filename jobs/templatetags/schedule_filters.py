from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split a string by the given argument"""
    return value.split(arg)

@register.filter
def stringformat(value, arg):
    """Format a string with the given format string"""
    try:
        return arg % value
    except (ValueError, TypeError):
        return value