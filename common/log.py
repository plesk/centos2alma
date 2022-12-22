import logging


class log():

    logger = logging.getLogger("distupgrader")

    @staticmethod
    def init_logger(logfile, loglevel=logging.INFO):
        log.logger.setLevel(loglevel)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        handler = logging.FileHandler(logfile) if logfile else logging.StreamHandler()
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