FROM alpine:3.19

# Instala dependências mínimas
RUN apk add --no-cache \
    python3 \
    py3-pip \
    cronie \
    tzdata \
    curl \
    && rm -rf /var/cache/apk/*

# Define timezone para América/São Paulo (UTC-3)
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Cria diretório de trabalho
WORKDIR /app

# Cria ambiente virtual e instala dependências Python
COPY requirements.txt .
RUN python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY app.py .
COPY cron_manager.py .

# Cria diretório para dados
RUN mkdir -p /data /var/log

# Expõe porta da API
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["/opt/venv/bin/python", "app.py"]