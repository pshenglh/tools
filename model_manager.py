# encoding: utf8

from copy import deepcopy
from flask import request
from datetime import datetime
from functools import wraps

import sys
reload(sys)
sys.setdefaultencoding('utf8')

from db.model import User, Company, Team, Pile, Video, Violation
from sqlalchemy import desc, func, inspect, String, extract
from db_session import Session, open_session


# 要求原子性的操作可传入session
def atomicity(commit=False):
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            session = kwargs.get('session')
            if not session:
                with open_session(Session, commit=commit) as session:
                    kwargs['session'] = session
                    r = func(*args, **kwargs)
            else:
                r = func(*args, **kwargs)
            return r
        return decorator
    return wrapper


class ModelManager(object):

    def __init__(self, model):
        self.model = model

    @atomicity()
    def get(self, model_id, session=None):
        model = session.query(self.model).get(model_id)

        if not model or model.is_del == 1:
            return -1

        return model

    @atomicity(commit=True)
    def update(self, model_id, attr_change=None, operation='', user_id=0, session=None, **kwargs):
        if not operation:
            operation = 'update'
        if not attr_change:
            attr_change = {}
        attr_change.update(kwargs)

        model = session.query(self.model).filter_by(id=model_id).scalar()

        if not model or (operation != 'restore' and model.is_del == 1):
            return -1

        for k, v in attr_change.items():
            if k in model.modified_column:
                setattr(model, k, v)

            # 删除时删除关联表记录
            if k == 'is_del' and hasattr(self.model, 'delete_relate'):
                for relate_model, field in self.model.delete_relate:
                    self._del_rel(session, relate_model, field, [model.id])

        session.add(model)

        return model_id

    # 递归删除关联的记录
    def _del_rel(self, session, model, field, ids):
        for model_id in ids:
            session.query(model).filter(getattr(model, field)==model_id)\
                        .update({'is_del': 1})

            if hasattr(model, 'delete_relate'):
                r_ids = session.query(model.id).filter(getattr(model, field)==model_id).all()
                if not r_ids:
                    return

                r_ids = [r[0] for r in r_ids]
                for relate_model, field, in model.delete_relate:
                    self._del_rel(session, relate_model, field, r_ids)

    @atomicity(commit=True)
    def add(self, data, session=None):
        if not data:
            return -1

        if not isinstance(data, list):
            data = [data]
        model_ids = []

        with open_session(Session, commit=True) as session:
            for d in data:
                model = self.model()
                model.add_model(d)
                session.add(model)
                session.flush()

                model_ids.append(model.id)

        if len(model_ids) < 2:
            return model_ids[0]
        else:
            return model_ids

    @atomicity(commit=True)
    def delete(self, model_id, session=None):
        res = self.update(model_id, operation='delete', is_del=1, session=session)

        return res

    def search_filter(self, query, filters):
        for k, v in filters.items():
            if v != 0 and not v:
                continue
            if isinstance(v, str):
                v = v.strip()
            if k.endswith('[]'):
                query = query.filter(getattr(self.model, k[:-2]).in_(v))
            elif k == 'start_time':
                query = query.filter(self.model.create_time>=datetime.strptime(v, '%Y%m%d%H%M%S'))
            elif k == 'end_time':
                query = query.filter(self.model.create_time<=datetime.strptime(v, '%Y%m%d%H%M%S'))
            elif getattr(self.model, k).type.python_type == str:
                value_pattern = '%{}%'.format(unicode(v))
                query = query.filter(getattr(self.model, k).like(value_pattern))
            else:
                query = query.filter(getattr(self.model, k)==v)

        return query

    @atomicity()
    def search(self, filters=None, offset=1, limit=10, not_del=True, session=None, **kwargs):
        offset = (offset - 1) * limit
        if filters == None:
            new_filters = {}
        else:
            new_filters = deepcopy(filters)

        new_filters.update(kwargs)

        query = session.query(self.model)

        query = self.search_filter(query, new_filters)

        if not_del and hasattr(self.model, 'is_del'):
            query = query.filter_by(is_del=0)

        total = query.with_entities(func.count(self.model.id)).scalar()
        models = query.order_by(desc(self.model.id)).offset(offset).limit(limit).all()

        return models, total

    @atomicity()
    def get_total(self, filters=None, not_del=True, session=None, **kwargs):
        if filters == None:
            new_filters = {}
        else:
            new_filters = deepcopy(filters)

        new_filters.update(kwargs)

        query = session.query(self.model)

        query = self.search_filter(query, new_filters)

        if not_del and hasattr(self.model, 'is_del'):
            query = query.filter_by(is_del=0)
        total = query.with_entities(func.count(self.model.id)).scalar()

        return total

    @atomicity()
    def search_all(self, filters=None, session=None, **kwargs):
        if filters == None:
            filters = {}

        filters.update(kwargs)

        query = session.query(self.model)

        for k, v in filters.items():
            if k.endswith('[]'):
                query = query.filter(getattr(self.model, k[:-2]).in_(v))
            elif getattr(self.model, k).type.python_type == str:
                value_pattern = '%{}%'.format(unicode(v))
                query = query.filter(getattr(self.model, k).like(value_pattern))
            else:
                query = query.filter(getattr(self.model, k)==v)

        total = query.with_entities(func.count(self.model.id)).scalar()
        models = query.order_by(desc(self.model.id)).all()

        return models, total

    @atomicity()
    def search_precise(self, filters=None, session=None, **kwargs):
        if filters == None:
            filters = {}

        filters.update(kwargs)

        query = session.query(self.model).filter_by(is_del=0)

        for k, v in filters.items():
            query = query.filter(getattr(self.model, k)==v)

        models = query.all()

        return models

    @atomicity()
    def search_field(self, dist_field, filters=None, session=None, **kwargs):
        if filters == None:
            filters = {}
        filters.update(kwargs)

        query = session.query(getattr(self.model, dist_field))
        if hasattr(self.model, 'is_del'):
            query = query.filter_by(is_del=0)

        query = self.search_filter(query, filters)
        results = query.all()

        results = [r[0] for r in results]

        return results

    def get_id_not_del(self):
        with open_session(Session) as rs:
            r = rs.query(func.min(self.model.id)).filter_by(is_del=0).scalar()
        
        return r

    def det_id_del(self):
        with open_session(Session) as rs:
            r = rs.query(func.min(self.model.id)).filter_by(is_del=1).scalar()

        return r

    def get_all(self, model_id):
        with open_session(Session) as rs:
            model = rs.query(self.model).get(model_id)

        return model

