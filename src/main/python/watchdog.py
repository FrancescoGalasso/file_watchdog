# -*- coding: utf-8 -*-

# pylint: disable=no-name-in-module
# pylint: disable=logging-format-interpolation

""" Main module """

import logging
import json
import os
import asyncio

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication
from qasync import QEventLoop


class MainWindow(QMainWindow):  # pylint: disable=too-few-public-methods
    """ Main Window """

    def __init__(self, ctx, config):
        super(MainWindow, self).__init__()  # pylint: disable=super-with-arguments
        self.ctx = ctx
        self.config = config
        self.ui_path = self.ctx.get_resource('main_window.ui')
        uic.loadUi(self.ui_path, self)

        logging.warning('config: {}'.format(self.config))

        self.pushButton.clicked.connect(lambda: self.test_func())

    def test_func(self):
        logging.warning('pushButton Clicked !')


class WatchdogApplication(QApplication):
    """ Watchdog Application """

    def __init__(self, fbs_ctx, main_window_class, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.__version = None
        self.__tasks = []
        self.__runners = []
        self.__config = self.__get_config(fbs_ctx)
        self.__init_event_loop()
        self.__init_tasks()

        # Instantiating MainWindow passed as 'main_windows_class'
        self.main_window = main_window_class(fbs_ctx, self.__config)

        logging.warning('self: {}'.format(self))

        self.run_forever()

    def __get_config(self, fbs_ctx, cfg_filename='watchdog.cfg'):       # pylint: disable=no-self-use
        try:
            filename_cfg = fbs_ctx.get_resource(cfg_filename)
            logging.warning('filename_cfg: {}'.format({filename_cfg}))
        except FileNotFoundError:
            logging.warning('{} not FOUND!'.format(cfg_filename))
            base_resources_path = fbs_ctx.get_resource()
            filename_cfg = ''.join([base_resources_path, os.sep, cfg_filename])
            with open(filename_cfg, 'w') as config_file:
                data = {
                    "ip": "",
                    "folder_path": "",
                    "api_endpoint": ""
                }
                json.dump(data, config_file, indent=4)

        finally:
            with open(filename_cfg, 'r') as f_alias:
                json_data = json.loads(f_alias.read())

            logging.warning('json_data: {}'.format(json_data))
            return json_data        # pylint: disable=lost-exception

    def __init_event_loop(self):
        loop = QEventLoop(self)
        asyncio.set_event_loop(loop)

    def __init_tasks(self):

        # self.__tasks = [self.__create_inner_loop_task()]
        file_watchdog_task = self.__file_watchdog_task(5)
        self.__tasks.append(file_watchdog_task)

    def __close_tasks(self):
        logging.warning('close all tasks')

        for t in self.__runners[:]:

            try:
                t.cancel()

                async def _coro(_):
                    await _
                self.loop.run_until_complete(_coro(t))

            except asyncio.CancelledError:
                logging.warning(f"{ t } has been canceled now.")

        self.__runners = []

    async def __create_inner_loop_task(self):
        try:

            self.processEvents()  # gui events
            await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            pass
        except Exception as e:  # pylint: disable=broad-except
            # self.handle_exception(e)
            logging.critical(e)

    async def __file_watchdog_task(self, sleep_time=5):
        from random import randint

        while True:
            random_value = randint(100, 200)
            logging.warning(f'[file watchdog task] - random number: {random_value}')
            await asyncio.sleep(sleep_time)

    def run_forever(self):

        self.main_window.show()

        try:

            self.__runners = [asyncio.ensure_future(t) for t in self.__tasks]
            self.loop = asyncio.get_event_loop()
            self.loop.run_forever()

        except KeyboardInterrupt:
            pass

        except Exception as e:  # pylint: disable=broad-except
            logging.critical('Exception: {}'.format(e))

        finally:

            logging.warning('close tasks')
            self.__close_tasks()

        self.loop.stop()
        self.loop.run_until_complete(
            self.loop.shutdown_asyncgens()
        )
        self.loop.close()
