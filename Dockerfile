FROM python:3.7.2-slim-stretch

RUN apt-get update \
    && apt-get -y install curl build-essential \
    && apt-get clean \
    && pip install --upgrade pip

# Prepare environment
RUN mkdir /freqtrade
WORKDIR /freqtrade

# Install TA-lib
COPY build_helpers/* /tmp/
RUN cd /tmp && /tmp/install_ta-lib.sh && rm -r /tmp/*ta-lib*

ENV LD_LIBRARY_PATH /usr/local/lib

# Install dependencies
COPY requirements.txt /freqtrade/
RUN pip install numpy --no-cache-dir \
  && pip install -r requirements.txt --no-cache-dir

# Install and execute
COPY . /freqtrade/
RUN pip install -e . --no-cache-dir
ENTRYPOINT ["freqtrade"]
