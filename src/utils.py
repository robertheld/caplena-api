import json

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)


class CaplenaObj(object):
    def __init__(self, **kwargs):
        pass

    def to_dict(self):
        return self.__dict__

    def reprJSON(self):
        return self.__dict__

    def __repr__(self):
        return json.dumps(self.__dict__, cls=ComplexEncoder)

    @classmethod
    def from_json(cls, json_data: dict):
        pass


