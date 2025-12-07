#!/usr/bin/env sh
set -exf

find . -name '*.pyc' -delete

python manage.py compilemessages --settings mcod.settings.test -v 3
python manage.py makemigrations --check --settings mcod.settings.test

exec pytest $@
