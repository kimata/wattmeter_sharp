FROM ubuntu:22.04

ENV TZ=Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    language-pack-ja \
    python3-docopt \
    python3-yaml python3-coloredlogs \
    python3-fluent-logger \
    python3-serial \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/wattmeter_sharp

COPY . .

CMD ["./app/sharp_hems_logger.py"]
