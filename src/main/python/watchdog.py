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
import requests

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from qasync import QEventLoop

sys.path.append('.')
from file_watchdog_exceptions import (MissingIP,
                                      MissingFolderPath,
                                      EmptyArguments,
                                      MultipleFlagActivated)
sys.path.remove('.')


WATCHDOG_CFG_FILE_NAME = 'watchdog.cfg'
CACHE = {}
ALFA40_SERVER_PORT = 8080
ALFA40_API_PREFIX = 'apiV1'

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

        self.__load_cfg()


    def handle_exception(self, err, ui_msg=None):  # pylint:  disable=no-self-use

        if not ui_msg:
            if hasattr(err, 'message'):
                ui_msg = err.message
            else:
                ui_msg = err

        logging.critical(f'err: {ui_msg}')
        self.update_gui_msg_board(ui_msg)

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

    def update_gui_msg_board(self, msg):
        formatted_date = datetime.datetime.fromtimestamp(time.time()).strftime('%d %b %y %H:%M:%S')
        msg = f'[{formatted_date}] {msg}\n'
        self.msg_board.insertPlainText(msg)

    def __get_folder_path(self):
        foo_dir = QFileDialog.getExistingDirectory(self, 'Select a directory')
        self.qline_folder_path.setText(foo_dir)

    def __save_cfg(self):
        folder_pth = self.qline_folder_path.text()
        ip = self.qline_ip.text()

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
                        save_msg = 'NEW CONFIG SAVED'
                        self.update_gui_msg_board(save_msg)

                except BaseException:   # pylint: disable=broad-except
                    print(traceback.format_exc())

        except (EmptyArguments, MissingIP, MissingFolderPath) as excp:
            self.handle_exception(excp)

    def __load_cfg(self):
        if CACHE.get('config'):
            current_config = CACHE.get('config')
            for elem in current_config:
                if 'ip' in elem:
                    _ip = current_config.get('ip')
                    self.qline_ip.setText(_ip)
                elif 'folder_path' in elem:
                    _folder_path = current_config.get('folder_path')
                    self.qline_folder_path.setText(_folder_path)
                elif 'api_endpoint' in elem:
                    _api_endpoint = current_config.get('api_endpoint')
                    self.qline_api_endpoint.setText(_api_endpoint)
                else:
                    pass


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
        self.__ip_reachable = False
        self.__ip_valid = False

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
                    "api_endpoint": "",
                    "alfadriver": 0,
                    "cr": 0,
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

        file_watchdog_task = self.__file_watchdog_task(4)
        self.__tasks.append(file_watchdog_task)

        ip_watchdog_task = self.__ip_watchdog_task(2)
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

    async def __file_watchdog_task(self, sleep_time=5):

        watchdog_folder_path = self.__config.get('folder_path')

        while True:

            logging.warning('__file_watchdog_task')
            tmp_lista = []
            for (dirpath, dirnames, filenames) in os.walk(watchdog_folder_path):
                tmp_lista += [os.path.join(dirpath, file) for file in filenames if '.bak' not in file]

            logging.warning(f'tmp_lista: {tmp_lista}')
            if tmp_lista:
                current_file = tmp_lista[0]
                current_file_bak = ''.join([current_file, '.bak'])

                logging.warning(f'current_file {current_file}')
                logging.warning(f'current_file_bak {current_file_bak}')
                self.upload_to_machine(current_file)

                if os.path.exists(current_file_bak):
                    os.remove(current_file_bak)
                os.rename(current_file, current_file_bak)

            await asyncio.sleep(sleep_time)

    async def __ip_watchdog_task(self, sleep_time=5):

        while True:
            alfa_device_ip = self.__config.get('ip')

            self.__ip_valid = self.ip_validator(alfa_device_ip)

            # check if IP is reachable if _valid_ip is True
            if self.__ip_valid:
                cmd_ = f"ping -n 1 -w 1000 {alfa_device_ip}"
                ping_process = await asyncio.create_subprocess_shell(cmd_, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                status = await ping_process.wait()
                logging.debug(f'status: {status}')
                if status == 0:
                    self.__ip_reachable = True

            logging.debug(f"self.__ip_valid: {self.__ip_valid} | self.__ip_reachable: {self.__ip_reachable}")

            self.main_window.update_gui_ip_infos(valid_ip=self.__ip_valid, reachable_ip=self.__ip_reachable)
            await asyncio.sleep(sleep_time)

    def upload_to_machine(self, current_file):
        # logging.warning(f' >>> current_file: {current_file}')

        device_ip = self.__config.get('ip')
        flag_alfadriver = self.__config.get('alfadriver')
        flag_cr = self.__config.get('cr')
        api_endpoint = self.__config.get('api_endpoint')

        # logging.debug(f'{device_ip} - flag_alfadriver {flag_alfadriver} - flag_cr {flag_cr}')

        try:

            if self.__ip_valid and self.__ip_reachable:
                if flag_alfadriver and flag_cr:
                    raise MultipleFlagActivated('PLEASE CHECK CONFIG FILE. DETECTED MULTIPLE FLAG ACTIVATED')

                if flag_alfadriver and not flag_cr:
                    self.__alfadriver_upload_formula_file(device_ip, current_file)
                elif not flag_alfadriver and flag_cr:
                    pass

                
        except MultipleFlagActivated as excp:
            # logging.critical(excp.message)
            self.main_window.handle_exception(excp)



    def ip_validator(self, ip_to_validate):
        # check if IP has a valid syntax
        flag_valid_ip = False
        regex = "^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"
        if re.search(regex, ip_to_validate):
            flag_valid_ip = True

        return flag_valid_ip

    def __alfadriver_upload_formula_file(self, ip, path_formula_file):

        uri_upload = "http://{}:{}/{}/{}".format(ip, ALFA40_SERVER_PORT, ALFA40_API_PREFIX, 'ad_hoc')

        with open(path_formula_file, 'r') as formula_file:
            lines = [line for line in formula_file]
            params = {'lines': lines}
            data = {'action': 'upload_file', 'params': params}
            logging.debug('params: {} | data API ad_hoc: {}'.format(params, data))
            try:
                r = requests.post(uri_upload, headers={'content-type': 'application/json'}, data=json.dumps(data), timeout=3)
                logging.warning("POST uri_upload:{}, data:{}, r.status_code:{}, r.reason:{}".format(
                                uri_upload, data, r.status_code, r.reason))

                if r.status_code == 200:
                    alfadriver_success_msg = 'FLINK SUCCESSFULLY SEND TO TINTING'
                    self.main_window.update_gui_msg_board(alfadriver_success_msg)
                else:
                    alfadriver_success_msg = 'ERROR ON SENDING FLINK TO TINTING'
                    self.main_window.update_gui_msg_board(alfadriver_success_msg)

            except requests.exceptions.RequestException as e:
                # print(e)
                result['error'] = True
                result['data'] = 'Dispenser not reachable ..'
                logging.critical(e)

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
