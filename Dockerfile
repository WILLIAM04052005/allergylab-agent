# Image du serveur en ligne d'AllergyLab (Render, ou tout hébergeur de conteneurs).
# La clé n'est jamais dans l'image : l'hébergeur la donne au démarrage, dans la
# variable ALLERGYLAB_CLE. Test en local :
#   docker build -t allergylab .
#   docker run -p 8000:8000 -e ALLERGYLAB_CLE=... allergylab
FROM python:3.12-slim

# uv, le même outil que sur nos machines.
RUN pip install --no-cache-dir "uv>=0.9,<0.14"

# Un utilisateur sans droits : le code écrit par le modèle ne tourne pas en root.
RUN useradd --create-home agent
WORKDIR /app

# Les dépendances d'abord (couche mise en cache), exactement celles de uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev && chown -R agent:agent /app

USER agent
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD [".venv/bin/python", "-m", "equipe.interface.serveur", "--en-ligne"]
