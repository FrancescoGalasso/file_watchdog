# -*- coding: utf-8 -*-

# pylint: disable=no-name-in-module
# pylint: disable=logging-format-interpolation

""" Main module """

import logging
import json
import os

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication


class MainWindow(QMainWindow):  # pylint: disable=too-few-public-methods
    """ Main Window """

    def __init__(self, ctx, config):
        super(MainWindow, self).__init__()  # pylint: disable=super-with-arguments
        self.ctx = ctx
        self.config = config
        self.ui_path = self.ctx.get_resource('main_window.ui')
        uic.loadUi(self.ui_path, self)

        logging.warning('config: {}'.format(self.config))
        logging.warning('self.ctx: {}'.format(self.ctx))


class WatchdogApplication(QApplication):
    """ Watchdog Application """

    def __init__(self, fbs_ctx, main_window_class, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.__version = None
        self.__tasks = []
        self.__runners = []
        self.__config = self.__get_config(fbs_ctx)

        # Instantiating MainWindow passed as 'main_windows_class'
        self.main_window = main_window_class(fbs_ctx, self.__config)

        self.__run_forever()

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
                json.dump(data, config_file)

        finally:
            with open(filename_cfg, 'r') as f_alias:
                json_data = json.loads(f_alias.read())

            logging.warning('json_data: {}'.format(json_data))
            return json_data        # pylint: disable=lost-exception

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
