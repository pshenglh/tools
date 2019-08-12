# !/usr/local/bin/python
# encoding: utf8

import time
import json
import unittest
import random
import string
from datetime import datetime
from io import BytesIO

import os
cwd = os.getcwd()
dwd = os.path.abspath(os.path.dirname(cwd))
os.chdir(dwd)

import sys
sys.path.append(os.getcwd())

from server import app

def get_token():
    app_client = app.test_client()
    post_data = dict(
        username='admin',
        password='admin'
    )

    rv = app_client.post('/api/login', data=json.dumps(post_data))
    data = json.loads(rv.data)
    token = data['token']
    return token

headers = {'token': get_token()}

def gen_random_name():
    name = ''.join(random.sample(string.ascii_letters+string.digits, 6))
    return name


def gen_random_digit(n=6):
    digit = ''.join(random.sample(string.digits, n))
    return digit


class BaseTest(object):

    def delete_test(self, obj_id, url, model):

        obj = self.model_manager.get_all(obj_id)
        rv = self.app.delete(url, headers=headers)
        code = json.loads(rv.data)['code']
        if not obj or obj.is_del:
            self.assertEqual(code, 410)
        else:
            self.assertEqual(code, 200)
            with open_write_session(LicWriteSession) as ws:
                obj = ws.query(model).get(obj_id)
                self.assertEqual(obj.is_del, 1)

                # obj.is_del = 0
                # ws.add(obj)

    def update_test(self, obj_id, url, data, model):

        with open_write_session(LicWriteSession) as ws:
            obj = ws.query(model).get(obj_id)
            old_data = {k: getattr(obj, k) for k in data.keys()}

        rv = self.app.patch(url, data=json.dumps(data), headers=headers)
        code = json.loads(rv.data)['code']
        if not obj or obj.is_del:
            self.assertEqual(code, 410)
        else:
            self.assertEqual(code, 200)

            with open_write_session(LicWriteSession) as ws:
                obj = ws.query(model).get(obj_id)

                for k, v in data.items():
                    if k == 'auth_func':
                        v = AuthFuncHandler().gen_auth_func(v)
                    if k == 'expire_ts':
                        continue
                    self.assertEqual(getattr(obj, k), v)

                for k, v in old_data.items():
                    setattr(obj, k, v)

                ws.add(obj)

    def get_test(self, url, obj_id):
        rv = self.app.get(url, headers=headers)
        code = json.loads(rv.data)['code']
        obj = self.model_manager.get_all(obj_id)
        if not obj or obj.is_del:
            self.assertEqual(code, 410)
        else:
            self.assertEqual(code, 200)



class UserTest(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

    def tearDown(self):
        pass


if __name__ == '__main__':
    suite = unittest.TestSuite()
    # suite.addTest(UserTest('test_upload_video'))
    suite.addTest(UserTest('test_delete_video'))
    unittest.TextTestRunner(verbosity=2).run(suite)
    
    # unittest.main()
