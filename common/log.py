import logging


class log():

    logger = logging.getLogger("distupgrader")

    @staticmethod
    def init_logger(logfiles, streams, console=False, loglevel=logging.INFO):
        log.logger.setLevel(loglevel)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        handlers = [logging.FileHandler('/dev/console', mode='w')] if console else []
        for logfile in logfiles:
            handlers.append(logging.FileHandler(logfile))
        for stream in streams:
            handlers.append(logging.StreamHandler(stream))

        for handler in handlers:
            handler.setLevel(level=logging.DEBUG)
            handler.setFormatter(formatter)
            log.logger.addHandler(handler)

    @staticmethod
    def debug(msg):
        log.logger.debug(msg)

    @staticmethod
    def info(msg):
        log.logger.info(msg)

    @staticmethod
    def warn(msg):
        log.logger.warn(msg)

    @staticmethod
    def err(msg):
        log.logger.error(msg)