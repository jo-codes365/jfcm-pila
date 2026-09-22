FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LIBREOFFICE_BINARY=/usr/bin/libreoffice

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        fontconfig \
        fonts-dejavu-core \
        fonts-liberation2 \
        fonts-crosextra-carlito \
        fonts-crosextra-caladea \
        fonts-noto-core \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        fonts-freefont-ttf \
        fonts-urw-base35 \
        libreoffice \
    && libreoffice --headless --version \
    && command -v libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Put organization-owned/licensed fonts in ./fonts before building. They are
# registered with fontconfig without modifying the uploaded presentation.
COPY fonts/ /usr/local/share/fonts/truetype/jfcm/
RUN fc-cache --force \
    && fc-match Calibri \
    && fc-match Cambria \
    && fc-match Arial

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY . .

EXPOSE 8000

CMD ["/bin/sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8000} --access-logfile - --error-logfile - app:app"]
