FROM python:3.7

WORKDIR /app

ADD dev-requirements.txt /app/dev-requirements.txt
ADD requirements.txt /app/requirements.txt
ADD game_of_graphql/ /app/game_of_graphql

RUN pip install -r dev-requirements.txt && \
    pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "-m", "game_of_graphql.server", "--host", "0.0.0.0"]
