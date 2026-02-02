ARG BUILD_DISTRO
FROM --platform=${TARGETPLATFORM} ${BUILD_DISTRO}

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get install -y curl pkg-config build-essential cmake git libssl-dev

ARG CPPLIBRARIES
ARG EXTRA_DOCKER_COMMANDS="echo No EXTRA_DOCKER_COMMANDS provided"

RUN /bin/bash -c "${CPPLIBRARIES}"
RUN /bin/bash -c "${EXTRA_DOCKER_COMMANDS}"

WORKDIR /work

ENTRYPOINT ["/bin/bash", "/work/src/backend/deployment/compilation/cpp/compile.bash"]