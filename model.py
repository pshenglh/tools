# encoding: utf8

from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, String, inspect, Float, Text
from db.db_session import Session


Base = declarative_base()
SECRET_KEY = 'secret_key'


class BaseModel(object):

    def _attr_filter(self, attr):
        if attr.startswith('_') or attr == 'is_del' or attr == 'password_hash':
            return False

        return True
    
    def to_dict(self):
        attrs = self.columns()
        attr_dict = {}
        for attr in attrs:
            if not self._attr_filter(attr):
                continue
            if attr.endswith('time'):
                attr_dict[attr] = getattr(self, attr).strftime('%Y.%m.%d')
            else:
                attr_dict[attr] = getattr(self, attr)

        return attr_dict

    def columns(self):
        return filter(self._attr_filter, inspect(self.__class__).all_orm_descriptors.keys())

    def add_model(self, data):
        columns = self.columns()
        for k, v in data.items():
            if k in columns:
                try:
                    setattr(self, k, v)
                except:
                    print k, v
                    raise

    def modify(self, data):
        for k, v in data.items():
            if k in self.modified_column:
                setattr(self, k, v)

