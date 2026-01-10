# reports/templatetags/report_filters.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        arg = float(arg)
        value = float(value)
        if arg != 0:
            return value / arg
        return 0
    except (ValueError, TypeError):
        return 0