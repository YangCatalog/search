FROM python:3.9
ARG YANG_ID
ARG YANG_GID
ARG CRON_MAIL_TO

ENV YANG_ID "$YANG_ID"
ENV YANG_GID "$YANG_GID"
ENV CRON_MAIL_TO "$CRON_MAIL_TO"
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1

EXPOSE 8005

ENV VIRTUAL_ENV=/search

#Install Cron
RUN apt-get -y update
RUN apt-get -y install cron gunicorn
RUN echo postfix postfix/mailname string yangcatalog.org | debconf-set-selections; \
    echo postfix postfix/main_mailer_type string 'Internet Site' | debconf-set-selections; \
    apt-get -y install postfix rsyslog systemd
RUN apt-get -y autoremove

COPY ./resources/main.cf /etc/postfix/main.cf

RUN groupadd -g ${YANG_GID} -r yang \
  && useradd --no-log-init -r -g yang -u ${YANG_ID} -d $VIRTUAL_ENV yang \
  && pip install virtualenv \
  && virtualenv --system-site-packages $VIRTUAL_ENV \
  && mkdir /etc/yangcatalog

COPY ./search $VIRTUAL_ENV

ENV PYTHONPATH=$VIRTUAL_ENV/bin/python
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR $VIRTUAL_ENV

RUN pip install -r requirements.txt

# Add crontab file in the cron directory
COPY ./search/crontab /etc/cron.d/elastic-cron

COPY ./search/scripts/pyang_plugin/json_tree.py /search/lib/python3.9/site-packages/pyang/plugins/.
COPY ./search/scripts/pyang_plugin/yang_catalog_index_es.py /search/lib/python3.9/site-packages/pyang/plugins/.

RUN mkdir /var/run/yang

RUN sed -i "s|<MAIL_TO>|${CRON_MAIL_TO} |g" /etc/cron.d/elastic-cron
RUN chown -R yang:yang $VIRTUAL_ENV
RUN chown yang:yang /etc/cron.d/elastic-cron
RUN chown -R yang:yang /var/run/yang

USER ${YANG_ID}:${YANG_GID}

# Apply cron job
RUN crontab /etc/cron.d/elastic-cron

RUN chmod 0644 /etc/cron.d/elastic-cron

ENV DJANGO_SETTINGS_MODULE=yang.settings

USER root:root

CMD chown -R yang:yang /var/run/yang && cron && service postfix start && service rsyslog start && /search/bin/gunicorn yang.wsgi:application -c gunicorn.conf.py

EXPOSE 8005
