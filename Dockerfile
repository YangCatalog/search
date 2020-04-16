FROM python:3
ARG YANG_ID
ARG YANG_GID

ENV YANG_ID "$YANG_ID"
ENV YANG_GID "$YANG_GID"
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1

EXPOSE 8005

env VIRTUAL_ENV=/search

#Install Cron
RUN apt-get update
RUN apt-get -y install cron vim uwsgi uwsgi-plugin-python3
RUN echo postfix postfix/mailname string yang2.amsl.com | debconf-set-selections; \
    echo postfix postfix/main_mailer_type string 'Internet Site' | debconf-set-selections; \
    apt-get -y install postfix
RUN apt-get autoremove -y

COPY main.cf /etc/postfix/main.cf

RUN groupadd -g ${YANG_GID} -r yang \
  && useradd --no-log-init -r -g yang -u ${YANG_ID} -d $VIRTUAL_ENV yang \
  && pip install virtualenv \
  && virtualenv --system-site-packages $VIRTUAL_ENV \
  && mkdir /etc/yangcatalog
COPY . $VIRTUAL_ENV

ENV PYTHONPATH=$VIRTUAL_ENV/bin/python
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR $VIRTUAL_ENV

RUN pip install -r requirements.txt \
  && pip install elasticsearch==6.4.0

# Add crontab file in the cron directory
COPY crontab /etc/cron.d/elastic-cron

COPY scripts/pyang_plugin/json_tree.py /search/lib/python3.8/site-packages/pyang/plugins/.
COPY scripts/pyang_plugin/yang_catalog_index_es.py /search/lib/python3.8/site-packages/pyang/plugins/.
COPY yang-search.ini-dist $VIRTUAL_ENV/yang-search.ini

RUN mkdir /var/run/yang

RUN chown -R yang:yang $VIRTUAL_ENV
RUN chown yang:yang /etc/cron.d/elastic-cron
RUN chown -R yang:yang /var/run/yang

USER ${YANG_ID}:${YANG_GID}

# Apply cron job
RUN crontab /etc/cron.d/elastic-cron

RUN chmod 0644 /etc/cron.d/elastic-cron

ENV DJANGO_SETTINGS_MODULE=yang.settings

USER root:root

CMD chown -R yang:yang /var/run/yang && cron && service postfix start && uwsgi --ini $VIRTUAL_ENV/yang-search.ini

EXPOSE 8005
