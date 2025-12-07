FROM docker.elastic.co/elasticsearch/elasticsearch:6.8.23

RUN mkdir /usr/share/elasticsearch/config/hunspell
RUN mkdir /usr/share/elasticsearch/config/synonyms

ADD ./docker/elasticsearch/stopwords.txt /usr/share/elasticsearch/config
ADD ./docker/elasticsearch/hunspell /usr/share/elasticsearch/config/hunspell
ADD ./docker/elasticsearch/synonyms /usr/share/elasticsearch/config/synonyms


RUN /usr/share/elasticsearch/bin/elasticsearch-plugin -s install analysis-stempel
RUN /usr/share/elasticsearch/bin/elasticsearch-plugin -s install analysis-icu

ADD ./docker/elasticsearch/setup-logging.sh /usr/local/bin/setup-logging
RUN chmod 755 /usr/local/bin/setup-logging

COPY ./docker/elasticsearch/elasticsearch.yml /usr/share/elasticsearch/config/elasticsearch.yml
