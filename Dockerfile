FROM python:3.7-slim-buster
RUN apt-get update && apt-get install -y git
#TODO
RUN git clone https://wwwin-github.cisco.com/obrigg/cisco-dnac-platform-syslog-audit
WORKDIR /cisco-dnac-platform-syslog-audit/
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "run.py"]
