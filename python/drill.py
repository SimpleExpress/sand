# coding=utf-8

import json
import logging
import requests
from pandas import DataFrame


class DrillRemoteException(Exception):
    pass


class DrillRestfulClient(object):
    def __init__(self, host, user, pwd):
        host = host.rstrip('/')
        self.login_service = host + '/j_security_check'
        self.query_service = host + '/query.json'

        self.user = user
        self.pwd = pwd
        self.cookies = None
        self.store_format = None
        self.headers = {'Content-type': 'application/json'}
        self.__initial_session('parquet')

    def __initial_session(self, default_store_format=None):
        response = requests.post(
            self.login_service, {
                'j_username': self.user,
                'j_password': self.pwd
            }
        )
        if (response.status_code == 200 and
            response.content.find('Log Out') > -1):
            self.cookies = response.cookies
            self.alter_store_format(default_store_format)
        else:
            raise DrillRemoteException('invalid login credential')

    def alter_store_format(self, store_format):
        if store_format and store_format != self.store_format:
            logging.info('alter store format as %s' % store_format)
            # no error will be returned for invalid format...
            self.query(
                "ALTER SESSION SET `store.format` = '%s'" % store_format,
                as_frame=False
            )
            self.store_format = store_format

    def query(self, query_string, store_format=None, as_frame=True):
        """
        :param query_string: the SQL query string.
        :param store_format: set store format for CTAS operation.
        :param as_frame: if true it will wrap the result into a pandas dataframe
        :return: the query result or raise exception if error happened.
        """

        self.alter_store_format(store_format)
        logging.info(query_string)
        _query = query_string.strip()
        if _query.endswith(';'):
            #  ending semicolon will cause remote error
            _query = _query[:-1]
        data = {
            'queryType': 'SQL',
            'query': _query
        }
        response = requests.post(
            self.query_service,
            data=json.dumps(data),
            headers=self.headers,
            cookies=self.cookies
        )
        if response.status_code == 200:
            try:
                result = json.loads(response.content)
            except ValueError:
                logging.warning('session may have been expired, '
                                'reconnect and try again.',
                                exc_info=True)
                self.__initial_session()
                return self.query(query_string, store_format, as_frame)
            else:
                rows = result.get('rows')
                if as_frame:
                    return DataFrame.from_records(rows)
                else:
                    return rows
        elif response.status_code == 500:
            # wrap errorMessage in the exception
            raise DrillRemoteException(response.content)
        else:
            raise DrillRemoteException('%s: %s' %
                                       (response.status_code, response.reason))
