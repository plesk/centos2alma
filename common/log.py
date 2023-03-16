import logging


DEFAULT_LOG_FILE = "/var/log/plesk/distupgrader.log"


class log():

    files_logger = logging.getLogger("distupgrader_files")
    streams_logger = logging.getLogger("distupgrader_streams")

    @staticmethod
    def init_logger(logfiles, streams, console=False, loglevel=logging.INFO):
        log.files_logger.setLevel(loglevel)
        log.streams_logger.setLevel(loglevel)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_handlers = []
        for logfile in logfiles:
            file_handlers.append(logging.FileHandler(logfile))

        stream_handlers = [logging.FileHandler('/dev/console', mode='w')] if console else []
        for stream in streams:
            stream_handlers.append(logging.StreamHandler(stream))

        for handler in file_handlers + stream_handlers:
            handler.setFormatter(formatter)

        for handler in file_handlers:
            log.files_logger.addHandler(handler)

        for handler in stream_handlers:
            log.streams_logger.addHandler(handler)

    @staticmethod
    def debug(msg, to_file=True, to_stream=True):
        if to_file:
            log.files_logger.debug(msg)

        if to_stream:
            log.streams_logger.debug(msg)

    @staticmethod
    def info(msg, to_file=True, to_stream=True):
        if to_file:
            log.files_logger.info(msg)

        if to_stream:
            log.streams_logger.info(msg)

    @staticmethod
    def warn(msg, to_file=True, to_stream=True):
        if to_file:
            log.files_logger.warn(msg)

        if to_stream:
            log.streams_logger.warn(msg)

    @staticmethod
    def err(msg, to_file=True, to_stream=True):
        if to_file:
            log.files_logger.error(msg)

        if to_stream:
            log.streams_logger.error(msg)
