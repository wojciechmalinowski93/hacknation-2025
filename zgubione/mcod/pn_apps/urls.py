from pathlib import Path

from bokeh.server.django import autoload
from bokeh.server.django.routing import document
from django.conf import settings
from django.urls import path

from mcod.pn_apps import stats_app, views

urlpatterns = [
    path("stats/", views.stats_dashboard, name="stats"),
    path("charts/slot-<int:slot>.png", views.chart_thumbnail),
    path("notebooks/<notebook>", views.short_apps),
]

notebooks_dir = Path(settings.ROOT_DIR + "notebooks")

bokeh_apps = [
    autoload("pn-apps/stats", stats_app.app),
]

for notebook in notebooks_dir.glob("*.ipynb"):
    notebook_path = "pn-apps/" + str(notebook.relative_to(settings.ROOT_DIR))
    bokeh_apps.append(document(notebook_path, notebook))
