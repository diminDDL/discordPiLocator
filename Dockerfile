# Based on https://github.com/ThatRedKite/thatkitebot/
FROM python:3.10-bullseye

WORKDIR /app/

COPY ./requirements.txt /tmp/requirements.txt
COPY ./pilocator /app/pilocator

WORKDIR /tmp/

RUN apt-get update && apt-get upgrade -y

RUN apt-get install -y git

RUN pip3 install --upgrade pip

RUN pip3 install -r requirements.txt

# until https://github.com/Pycord-Development/pycord/issues/1840 is fixed we have to use an older version
# RUN pip3 install -U "py-cord[speed]"
RUN pip3 install -U "py-cord[speed]"==2.3.0

WORKDIR /app/

