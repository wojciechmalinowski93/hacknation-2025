FROM postgres:13-trixie

RUN mkdir /dumps
RUN chmod 655 /dumps

ADD ./docker/postgres/postgresql.conf /etc/postgresql
RUN chmod 644 /etc/postgresql/postgresql.conf

CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
