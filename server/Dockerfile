FROM tiangolo/uwsgi-nginx-flask:python3.8

COPY ./ /app

WORKDIR /app

RUN apt update
RUN apt install -y librsvg2-bin
RUN pip install -r requirements.txt
RUN ./makepng