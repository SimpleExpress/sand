# coding=utf-8

import re
import six
import json


class ConfigKeyError(Exception):
    pass


class Configuration(dict):
    """
    A dict like object only allows keys as string, and the keys should be
    valid identifier, i.e.
    - starts with with [a-zA-Z_$]
    - allows characters in [a-zA-Z\d_$]

    besides, it allows nested key separated by dot(.), e.g.
      config = Configuration()
      config['a.b.c'] = 1
    the code above will result in a dict like this:
    {
        a: {
            b: {
                c: 1
            }
        }
    }
    """

    def __init__(self, iterable=(), **kwargs):
        super(Configuration, self).__init__(iterable, **kwargs)
        Configuration.__make_configurable(self)

    @staticmethod
    def __make_configurable(configurable):
        def make(item):
            if isinstance(item, dict):
                for k, v in item.items():
                    k = str(k)
                    v = make(v)
                    item[k] = v
                return Configuration(item)
            elif isinstance(item, (list, tuple)):
                for i in range(len(item)):
                    item[i] = make(item[i])
                return item
            else:
                return item

        assert isinstance(configurable, Configuration)
        for key, value in configurable.items():
            key = str(key)
            value = make(value)
            configurable[key] = value

    @staticmethod
    def from_file(files):
        if not isinstance(files, (list, tuple)):
            files = [files, ]

        container = {}
        for p in files:
            d = {}
            six.exec_(p, d)
            container.update(d)

        try:
            del container['__builtins__']
        except KeyError:
            pass
        return Configuration(container)

    @staticmethod
    def from_json(files):
        if not isinstance(files, (list, tuple)):
            files = [files, ]

        container = {}
        for p in files:
            with open(p) as fh:
                content = fh.read()
                container.update(json.loads(content))
        return Configuration(container)

    def to_json(self, path):
        with open(path, 'w') as fh:
            fh.write(json.dumps(self, indent=2, sort_keys=True))

    def __find_container(self, names):
        container = self
        while names:
            name = names.pop(0)
            if name in container:
                container = super(Configuration, container).__getitem__(name)
                if not isinstance(container, Configuration):
                    return name
            else:
                return name
        else:
            return container

    def __getitem__(self, item):
        self.__check_name(item)
        names = item.split('.')
        entry = names.pop()
        container = self.__find_container(names)
        if isinstance(container, Configuration):
            if super(Configuration, container).__contains__(entry):
                return super(Configuration, container).__getitem__(entry)
            else:
                raise KeyError('key not found: %s (%s)' % (entry, item))
        else:
            raise KeyError('key not found: %s (%s)' % (container, item))

    def __setitem__(self, key, value):
        self.__check_name(key)
        names = key.split('.')
        entry = names.pop()
        container = self
        while names:
            name = names.pop(0)
            if name not in container:
                container[name] = Configuration()
            container = container.get(name)
        super(Configuration, container).__setitem__(entry, value)

    def __delitem__(self, key):
        self.__check_name(key)
        names = key.split('.')
        entry = names.pop()
        container = self.__find_container(names)
        if isinstance(container, Configuration):
            super(Configuration, container).__delitem__(entry)
        else:
            raise KeyError('key not found: %s' % key)

    def __contains__(self, item):
        try:
            self.__check_name(item)
        except ConfigKeyError:
            return False
        else:
            names = item.split('.')
            entry = names.pop()
            container = self.__find_container(names)
            if isinstance(container, Configuration):
                return super(Configuration, container).__contains__(entry)
            else:
                return False

    def get(self, k, d=None):
        try:
            self.__check_name(k)
        except ConfigKeyError:
            return d
        else:
            names = k.split('.')
            entry = names.pop()
            container = self.__find_container(names)
            if isinstance(container, Configuration):
                return super(Configuration, container).get(entry, d)
            else:
                return d

    def pop(self, k, d=None):
        value = self[k]
        del self[k]
        return value

    def has_key(self, k):
        return self.__contains__(k)

    @staticmethod
    def __check_name(name):
        regex = re.compile('^[a-zA-Z_$][a-zA-Z\d_$]*'
                           '(\.[a-zA-Z_$][a-zA-Z\d_$]*)*$')
        if not isinstance(name, six.text_type):
            raise ConfigKeyError('configuration key must be string: %s' % name)
        if not regex.match(name):
            raise ConfigKeyError('illegal configuration key: %s' % name)
