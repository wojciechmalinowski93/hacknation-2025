FROM python:3.8.16

ARG UID=1000
ARG GID=1000
ARG UNAME=mcod

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository "deb http://deb.debian.org/debian bullseye main contrib non-free"
RUN apt-get update && apt-get install -y --allow-unauthenticated \
    gettext \
    locales \
    libarchive13 \
    libmagickcore-6.q16-3-extra \
    curl \
    dirmngr \
    apt-transport-https \
    lsb-release \
    ca-certificates \
    firefox-esr \
    ffmpeg \
    unrar \
    libxmlsec1-dev

RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -

RUN apt-get install -y nodejs

RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen
RUN sed -i '/pl_PL.UTF-8/s/^# //g' /etc/locale.gen
RUN locale-gen

ENV LANG=pl_PL.UTF-8
ENV LANGUAGE=pl_PL:pl
ENV LC_ALL=pl_PL.UTF-8

ENV OPENSSL_CONF=/etc/ssl/

RUN npm install -g geckodriver --unsafe-perm

RUN groupadd -g $GID -o $UNAME
RUN useradd -m -u $UID -g $GID -o -s /bin/bash $UNAME

WORKDIR /usr/src/mcod_backend

RUN pip install -I setuptools"<58" "pipenv==2022.10.12"

ADD Pipfile.lock /usr/src/mcod_backend/Pipfile.lock
ADD Pipfile      /usr/src/mcod_backend/Pipfile
ADD django_logingovpl-0.0.5-py3-none-any.whl /usr/src/mcod_backend/django_logingovpl-0.0.5-py3-none-any.whl
ADD django_suit-0.2.28-py3-none-any.whl      /usr/src/mcod_backend/django_suit-0.2.28-py3-none-any.whl
ADD hypereditor-0.1.0-py3-none-any.whl       /usr/src/mcod_backend/hypereditor-0.1.0-py3-none-any.whl
RUN pipenv --verbose install --deploy --system

COPY ./docker/wait-for-it.sh /usr/local/bin/wait-for-it
RUN chmod +x /usr/local/bin/wait-for-it

COPY ./docker/app/start-api.sh /usr/local/bin/start-api
RUN chmod +x /usr/local/bin/start-api

COPY ./docker/app/start-django.sh /usr/local/bin/start-django
RUN chmod +x /usr/local/bin/start-django

COPY ./docker/app/start-celery.sh /usr/local/bin/start-celery
RUN chmod +x /usr/local/bin/start-celery

ADD . /usr/src/mcod_backend
RUN python manage.py compilemessages --settings mcod.settings.test -v 3

EXPOSE 8001 5678
