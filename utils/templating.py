"""
Single shared Jinja2 template environment.

Previously every route module constructed its own `Jinja2Templates(...)`, which
duplicated the environment 13 times and made it impossible to register globals
(such as the CSRF token) in one place.
"""

from fastapi.templating import Jinja2Templates

from config import BASE_DIR
from utils.security import get_csrf_token
from utils.time_helper import to_local


def _csrf_processor(request):
    return {"csrf_token": get_csrf_token(request)}


templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates"),
    context_processors=[_csrf_processor],
)

# Renders a stored UTC timestamp in the shop's local timezone.
templates.env.filters["localtime"] = to_local
