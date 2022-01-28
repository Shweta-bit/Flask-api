FROM gcpapp02

WORKDIR /flaskapp01

RUN apt-get install python3

COPY reuirments.txt reuirments.txt

RUN pip install -r reuirments.txt

COPY ./app ./app

CMD ["python3", "./app/main.py"]