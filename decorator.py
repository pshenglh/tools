# encoding: utf8

import time
import logging
import functools
from flask import request
from utils import response
from db.model import User


def error_handler(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        try:
            st = time.time()
            r = func(*args, **kwargs)
            logging.info('{}: cost {}'.format(request.url, time.time()-st))
            return r
        except Exception as err:
            logging.exception('{}: {}'.format(request.url, err))
            return response.server_error()

    return decorator


def check_login(f):
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        try:
            start_time = time.time()
            token = request.headers.get('token')
            user = User.verify_auth_token(token)

            if not user:
                return response.log_timeout()

            request.user = user
            r = f(*args, **kwargs)
            logging.info('{} cost:{}'.format(request.url, (time.time()-start_time)))

            return r
        except Exception as err:
            logging.exception('{}, {}, {}'.format(request.url, request.method, err))
            return response.server_error()

    return decorator


def check_permission(permission):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                start_time = time.time()
                token = request.headers.get('token')
                user = User.verify_auth_token(token)

                if not user:
                    return response.log_timeout()

                if not (user.permission & permission):
                    return response.unauthorized()

                request.user = user
                r = f(*args, **kwargs)
                logging.info('{} cost:{}'.format(request.url, (time.time()-start_time)))

                return r
            except Exception as err:
                logging.exception('{}, {}, {}'.format(request.url, request.method, err))
                return response.server_error()

        return wrapper

    return decorator

