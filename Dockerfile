FROM tiangolo/uwsgi-nginx-flask:python3.7

RUN pip install Pillow requests Flask-Limiter Astral python-dotenv google-api-python-client google-auth-oauthlib
