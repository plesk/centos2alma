# The Dockerfile was brought from the repository build-with-buck
# https://github.com/SandakovMM/build-with-buck
# But little changed. Because GitHub actions mount sourcecode inside
# the action, but we should do the same inside the container manually.
# So to build you shoud just call docker like this:
# > docker run -v ./:/target [container-name] build :centos2alma
FROM openjdk:8

MAINTAINER mmsandakov@gmail.com

# Prepare environment
RUN apt-get update && apt-get install -y git ant build-essential gcc python python-dev python3-distutils
RUN useradd -m -s /bin/false buck
RUN mkdir /buck && chown buck /buck
USER buck

# Build buck
# We could just clone because I don't expect buck to be updated in this repository
# ToDo: move to buck2
RUN git clone https://github.com/facebook/buck.git /buck/
RUN cd /buck && ant

# We shoul return to root because github actions expects it
USER root
RUN ln -sf /buck/bin/buck /usr/bin/ ; mkdir /target
WORKDIR /target

ENTRYPOINT ["/usr/bin/buck"]