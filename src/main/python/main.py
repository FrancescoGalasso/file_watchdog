# -*- coding: utf-8 -*-

# pylint: disable=no-name-in-module

""" Main module """

import sys
from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property


class WatchdogAppContext(ApplicationContext):
    """ FBS Watchdog App Context """

    @cached_property            #pylint: disable=missing-function-docstring
    def app(self):
        sys.path.append('.')
        import watchdog   # pylint: disable=import-error, import-outside-toplevel
        sys.path.remove('.')

        application = watchdog.WatchdogApplication(self, watchdog.MainWindow, sys.argv)
        return application


if __name__ == '__main__':
    appctxt = WatchdogAppContext()
    exit_code =  appctxt.app.exec_()
    sys.exit(exit_code)
