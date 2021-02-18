# -*- coding: utf-8 -*-

"""
file_watchdog.exceptions
~~~~~~~~~~~~~~~~~~~
This module contains the set of FileWatchdog exceptions.
"""


class FileWatchdogBaseException(Exception):
    """There was an ambiguous exception that occurred while handling your
    request.
    """

    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)
    # pass


class MissingIP(FileWatchdogBaseException, ValueError):
    """The IP is missing."""


class MissingFolderPath(FileWatchdogBaseException, ValueError):
    """The destination path is missing."""


class EmptyArguments(FileWatchdogBaseException):
    """ Empty IP and FOLDER arguments are passed"""

class MultipleFlagActivated(FileWatchdogBaseException):
	""" Retrieved both alfadriver and cr flag from config file"""
