ARG LINUX_DISTRO
FROM --platform=${TARGETPLATFORM} ${LINUX_DISTRO}

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get install -y curl pkg-config build-essential cmake git libssl-dev

ARG CPPLIBRARIES
ARG EXTRA_DOCKER_COMMANDS

RUN /bin/bash -c "apt-get update && ${CPPLIBRARIES}"
RUN if [ -n "$EXTRA_DOCKER_COMMANDS" ]; then apt-get update && /bin/bash -c "$EXTRA_DOCKER_COMMANDS"; else echo No EXTRA_DOCKER_COMMANDS provided; fi

WORKDIR /work

ENTRYPOINT ["/bin/bash"]