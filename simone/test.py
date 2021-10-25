from django.test.runner import DiscoverRunner
from io import StringIO
from logging import StreamHandler, getLogger
from unittest import TextTestRunner, TextTestResult


class SimoneTestRunner(TextTestRunner):
    def __init__(self, *args, **kwargs):
        kwargs['buffer'] = True
        super().__init__(*args, **kwargs)


class SimoneTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._stream = StringIO()
        self._stream_handlers = [StreamHandler(self._stream)]
        self._root_logger = getLogger()
        self._original_handlers = self._root_logger.handlers

    def startTest(self, test):
        self._stream.truncate(0)
        self._root_logger.handlers = self._stream_handlers
        return super().startTest(test)

    def stopTest(self, test):
        self._root_logger.handlers = self._original_handlers
        return super().startTest(test)

    # i don't like overriding a _ property, but otherwise we'd have to
    # reimplement ~3 add* methods, one of which is non-trivial, which seems
    # more likely to be flakey. Essentially we don't want ot mirror the output
    # during the test runs when _restoreStdout is called so this effectively
    # disables the property that gets set to cause that to happen.
    @property
    def _mirrorOutput(self):
        return False

    @_mirrorOutput.setter
    def _mirrorOutput(self, val):
        pass

    # same here :-(. This is so that we can include any logging for the failed
    # tests.
    def _exc_info_to_string(self, err, test):
        return (
            super()._exc_info_to_string(err, test)
            + '\nLogging:\n'
            + self._stream.getvalue()
        )


class SimoneRunner(DiscoverRunner):

    test_runner = SimoneTestRunner

    def get_resultclass(self):
        ret = super().get_resultclass()
        if ret is None:
            ret = SimoneTestResult
        return ret
