FROM python:3.6.9-alpine as builder

RUN apk update && apk add --update git
RUN mkdir "temp/" && cd temp \
&& git clone https://github.com/voightp/esofile-reader.git
RUN cd temp && cd esofile-reader && python setup.py sdist

FROM builder

WORKDIR "app/"

RUN apk add --no-cache python3-dev libstdc++ && \
    apk add --no-cache g++
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --from=builder /temp/esofile-reader/dist /esoreader/
RUN pip install --no-cache-dir dist/eso_reader-0.0.1.tar.gz

COPY . .

RUN python main.py


