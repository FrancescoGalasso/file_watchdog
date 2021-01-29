# -*- coding: utf-8 -*-

# pylint: disable=no-name-in-module
# pylint: disable=logging-format-interpolation

""" Main module """

import logging

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication


class MainWindow(QMainWindow):  # pylint: disable=too-few-public-methods
    """ Main Window """

    def __init__(self, ctx):
        super(MainWindow, self).__init__()  # pylint: disable=super-with-arguments
        self.ctx = ctx
        self.ui_path = self.ctx.get_resource('main_window.ui')
        uic.loadUi(self.ui_path, self)


class WatchdogApplication(QApplication):
    """ Watchdog Application """

    def __init__(self, fbs_ctx, main_window_class, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.__version = None
        self.__tasks = []
        self.__runners = []

        # Instantiating MainWindow passed as 'main_windows_class'
        self.main_window = main_window_class(fbs_ctx)

        self.__run_forever()

    def __run_forever(self):

        self.main_window.show()

        try:

            logging.warning('asyncio.ensure_future __tasks')

        except KeyboardInterrupt:
            pass

        except Exception as e:  # pylint: disable=broad-except
            # self.handle_exception(e)
            logging.critical('Exception: {}'.format(e))

        finally:

            logging.warning('close tasks')
