# We use an image with pre-build buck since first version of buck is preatty antique already
# so we don't want to build it from scratch each time.
# This image is based on Ubuntu 22.04 with pre-installed OpenJDK 8 and buck
FROM msandakov/buck-ubt22:1.0

# Prepare environment
RUN apt update && apt install -y git build-essential gcc clang \
    python2 python3 python3-dev zlib1g-dev openssl libssl-dev curl \
    libbz2-dev liblzma-dev libsqlite3-dev libreadline-dev

# Use runner user to make sure we work as files owner (default github action user)
RUN adduser --disabled-password --gecos "" --uid 1001 runner \
    && groupadd docker --gid 123 \
    && usermod -aG sudo runner \
    && usermod -aG docker runner \
    && echo "%sudo   ALL=(ALL:ALL) NOPASSWD:ALL" > /etc/sudoers \
    && echo "Defaults env_keep += \"DEBIAN_FRONTEND\"" >> /etc/sudoers

USER runner

ENV HOME /home/runner
ENV PYENV_ROOT $HOME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

# Make sure we have exactly python 3.6.8 installed. Because I need this version of python for my projects.
# You could freely change it to any other version. Or remove pyenv at all if you fine
# with the default python version (3.9 for this container).
# ToDo: find a way to configure python version from an action configuration
RUN curl https://pyenv.run | bash
# We want to use clang because modern gcc work bad with outrated python versions
RUN CC=clang pyenv install 3.6.15
RUN pyenv global 3.6.15

USER root
# A little hack to avoid all tihs .pyenv pathes in .buckconfig files. Looks not so bad I suppose
RUN ln -sf $HOME/.pyenv/shims/python3.6 /usr/bin/python3.6

USER runner

WORKDIR /home/runner/project

ENTRYPOINT ["/usr/bin/buck"]