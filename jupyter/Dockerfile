FROM python:3.11-slim-bookworm

# Java pour PySpark ; utilisateur non root "jovyan" (même chemin de travail que les images Jupyter)
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 -s /bin/bash jovyan \
    && mkdir -p /home/jovyan/work \
    && chown -R jovyan:jovyan /home/jovyan

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# soda-core-mysql 3.3.5 impose mysql-connector-python 8.0.30, qui échoue sur MariaDB 10.6 et plus
# (« Character set 'utf8' unsupported ») ; corrigé à partir de la 8.0.33.
RUN pip install --no-cache-dir --no-deps mysql-connector-python==8.4.0

USER jovyan
WORKDIR /home/jovyan/work
EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser"]
