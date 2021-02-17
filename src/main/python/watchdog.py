# -*- coding: utf-8 -*-

# pylint: disable=no-name-in-module
# pylint: disable=logging-format-interpolation
# pylint: disable=logging-fstring-interpolation
# pylint: disable=missing-function-docstring

""" Main module """

import logging
import json
import os
import asyncio
import sys
import re
import datetime
import time
import traceback

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from qasync import QEventLoop

sys.path.append('.')
from file_watchdog_exceptions import (MissingIP,
                                      MissingFolderPath,
                                      EmptyArguments)
sys.path.remove('.')


WATCHDOG_CFG_FILE_NAME = 'watchdog.cfg'
CACHE = {}

class MainWindow(QMainWindow):  # pylint: disable=too-few-public-methods
    """ Main Window """

    def __init__(self, ctx):
        super(MainWindow, self).__init__()  # pylint: disable=super-with-arguments
        self.ctx = ctx
        self.ui_path = self.ctx.get_resource('main_window.ui')
        uic.loadUi(self.ui_path, self)

        gray = self.ctx.get_resource('images\\gray.png')
        pixmap_gray = QPixmap(gray).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_reach_lbl.setPixmap(pixmap_gray)
        self.img_valid_ip.setPixmap(pixmap_gray)

        self.btn_home.clicked.connect(self.on_btn_home_clicked)
        self.btn_cfg.clicked.connect(self.on_btn_config_clicked)
        self.btn_open_folder_files.clicked.connect(self.__get_folder_path)
        self.btn_save_cfg.clicked.connect(self.__save_cfg)


    def handle_exception(self, err, timestamp, ui_msg=None):  # pylint:  disable=no-self-use

        if not ui_msg:
            if hasattr(err, 'message'):
                ui_msg = err.message
            else:
                ui_msg = err

        logging.critical(f'err: {ui_msg}')
        excp_message_board = f'[{timestamp}] {ui_msg}\n'
        self.msg_board.insertPlainText(excp_message_board)

    def on_btn_home_clicked(self):
        self.main_window_stack.setCurrentWidget(self.home)

    def on_btn_config_clicked(self):
        self.main_window_stack.setCurrentWidget(self.config)

    def update_gui_ip_infos(self, valid_ip, reachable_ip):

        red = self.ctx.get_resource('images\\red.png')
        green = self.ctx.get_resource('images\\green.png')
        pixmap_red = QPixmap(red).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap_green = QPixmap(green).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        if valid_ip is True:
            self.img_valid_ip.setPixmap(pixmap_green)
        elif valid_ip is False:
            self.img_valid_ip.setPixmap(pixmap_red)

        if reachable_ip is True:
            self.img_reach_lbl.setPixmap(pixmap_green)
        elif reachable_ip is False:
            self.img_reach_lbl.setPixmap(pixmap_red)

    def __get_folder_path(self):
        foo_dir = QFileDialog.getExistingDirectory(self, 'Select a directory')
        self.qline_folder_path.setText(foo_dir)

    def __save_cfg(self):
        folder_pth = self.qline_folder_path.text()
        ip = self.qline_ip.text()
        formatted_date = datetime.datetime.fromtimestamp(time.time()).strftime('%d %b %y %H:%M:%S')

        try:

            if ip.rstrip() == "" and folder_pth == "" :
                raise EmptyArguments('PLEASE FILL EMPTY IP FIELD AND SELECT A FOLDER')

            elif ip.rstrip() == "":
                raise MissingIP('PLEASE FILL EMPTY IP FIELD')

            elif folder_pth == "":
                raise MissingFolderPath('PLEASE SELECT A FOLDER')

            else:

                try:
                    logging.debug(f'config: {self.config}')
                    with open(self.ctx.get_resource(WATCHDOG_CFG_FILE_NAME), 'w') as f_alias:
                        if CACHE.get('config'):
                            old_config = CACHE.get('config')
                            old_config.update({'ip': ip})
                            old_config.update({'folder_path': folder_pth})
                        json.dump(old_config, f_alias, indent=2)
                        save_msg = f'[{formatted_date}] NEW CONFIG SAVED'
                        self.msg_board.insertPlainText(save_msg)

                except BaseException:   # pylint: disable=broad-except
                    print(traceback.format_exc())

        except (EmptyArguments, MissingIP, MissingFolderPath) as excp:
            self.handle_exception(excp, formatted_date)


class WatchdogApplication(QApplication):
    """ Watchdog Application """

    def __init__(self, fbs_ctx, main_window_class, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.__version = None
        self.__tasks = []
        self.__runners = []
        self.__config = self.__get_config(fbs_ctx)
        self.__async_qt_event_loop = self.__init_async_event_loop()
        self.__init_tasks()

        # Instantiating MainWindow passed as 'main_windows_class'
        self.main_window = main_window_class(fbs_ctx)

        logging.warning('self: {}'.format(self))

        self.run_forever()

    def __get_config(self, fbs_ctx, cfg_filename=WATCHDOG_CFG_FILE_NAME):       # pylint: disable=no-self-use
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

            CACHE.update({'config': json_data})
            return json_data        # pylint: disable=lost-exception

    def __init_async_event_loop(self):
        qt_event_loop = QEventLoop(self)
        asyncio.set_event_loop(qt_event_loop)
        return qt_event_loop

    def __init_tasks(self):

        # self.__tasks = [self.__create_inner_loop_task()]
        file_watchdog_task = self.__file_watchdog_task(5)
        self.__tasks.append(file_watchdog_task)

        ip_watchdog_task = self.__ip_watchdog_task(3)
        self.__tasks.append(ip_watchdog_task)

    def __close_tasks(self):
        logging.warning('close all tasks')

        tasks = [task for task in asyncio.all_tasks(self.loop) if not task.done()]
        logging.warning(f'tasks: {tasks}')

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
            # logging.warning(f'[file watchdog task] - random number: {random_value}')
            await asyncio.sleep(sleep_time)
            # for (dirpath, dirnames, filenames) in os.walk(path_to_dir):

    async def __ip_watchdog_task(self, sleep_time=5):
        _valid_ip = False
        _reachable_ip = False

        while True:
            alfa_device_ip = self.__config.get('ip')

            # check if IP has a valid syntax
            regex = "^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"
            if re.search(regex, alfa_device_ip): 
                _valid_ip = True

            # check if IP is reachable if _valid_ip is True
            if _valid_ip:
                cmd_ = f"ping -n 1 -w 1000 {alfa_device_ip}"
                ping_process = await asyncio.create_subprocess_shell(cmd_, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                status = await ping_process.wait()
                logging.debug(f'status: {status}')
                if status == 0:
                    _reachable_ip = True

            logging.debug(f"_valid_ip: {_valid_ip} | _reachable_ip: {_reachable_ip}")

            self.main_window.update_gui_ip_infos(valid_ip=_valid_ip, reachable_ip=_reachable_ip)
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

        sys.exit(self.__async_qt_event_loop)
