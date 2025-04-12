from django import template

register = template.Library()

@register.filter
def format_runtime(minutes):
    if minutes is None:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h:{mins}m"