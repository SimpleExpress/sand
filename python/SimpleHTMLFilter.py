import copy
from html.parser import HTMLParser
from functools import partial


class SimpleHTMLFilter(HTMLParser):
    """ Example:
<form name="form1" action="/action" method="post">
    <p name="message">Available Options</p>
    <input type="hidden" name="task" value="uid">
    <table>
        <tr align="left">
            <td><b>Select an option: </b></td>
            <td>
                <select name="app">
                    <option value="value 1">value 1
                    <option value="value 2">value 2
                </select>
            </td>
        </tr>
    </table>
    <p><input type="submit" name="submit" value="submit"></p>
</form>

def match_attr(to_, from_):
    return all([item in to_ for item in from_])
P = lambda from_: partial(match_attr, from_=from_)

{
    # match 'form' tag has name = 'form1' then output its 'action'
    # attribute as 'post_url'
    'tag': 'form',
    'matcher': P([('name', 'form1')])
    'out': [('action', 'post_url')],
    'children':
    (
        # for descendant, match 'select' tag has name = 'app'
        {
            'tag': 'select',
            'matcher': P([('name', 'app')])
            'children':
            (
                # for descendants match any 'option' tag and output
                # 'value' attribute as 'app'
                {
                    'tag': 'option',
                    'out': [('value', 'app')]
                }
            )
        },
        # for descendants match 'input' tag has name = 'task',
        # output 'value' attribute as 'task'
        {
            'tag': 'input',
            'matcher': P([('name', 'task')])
            'out': [('value', 'task')]
        },
        # for descendants match 'p' tag has name = 'message',
        # output its data as 'message'
        {
            'tag': 'p',
            'matcher': P([('name', 'message')])
            'children':
            (
                {
                    'out': 'message'
                }
            )
        }
    )
}"""

    def __init__(self, filters):
        HTMLParser.__init__(self)
        HTMLParser.reset(self)
        self._stack = []
        self._flag_pool = {}
        self._value_pool = {}

        self._starttag_handlers = []
        self._endtag_handlers = []
        self._data_handlers = []
        self._install_filters(filters)

    def reset(self):
        HTMLParser.reset(self)
        self._stack = []
        self._flag_pool = {}
        self._value_pool = {}

    @staticmethod
    def _generate_flag(pre_flag, flag):
        if not pre_flag:
            pre_flag = 'filter'
        return '%s::%s' % (pre_flag, flag)

    def _install_filters(self, filters, ptype=None, pre_flag=None):
        """
        HtmlFilter = {
            'tag':
                - tag handler: tag name
                - data handler: None
            'matcher': matcher function that will be called with element attrs
            'out':
                - attributes: (attr_name, saved_name), ...
                - data: saved_name
            'descendants': filters, ...
        }
        """
        assert ptype in ('ATTR', 'DATA', None)
        for i in range(len(filters)):
            html_filter = filters[i]
            assert id(html_filter) not in self._stack, \
                'Recursive filters detected'
            self._stack.append(id(html_filter))
            tag = html_filter.get('tag', None)
            matcher = html_filter.get('matcher', None)
            output = html_filter.get('out', [])
            descendants = html_filter.get('descendants', [])
            if not matcher:
                matcher = lambda x: True
            new_flag = self._generate_flag(pre_flag, i)
            if tag:  # Attributes filter
                if descendants:
                    self._install_filters(descendants, 'ATTR', new_flag)
                self._starttag_handlers.append(
                    partial(self._start_tag, tag_=tag, matcher=matcher,
                            output=output, pre_flag=pre_flag,
                            pos_flag=new_flag))
                self._endtag_handlers.append(
                    partial(self._end_tag, tag_=tag, flag=new_flag))
            else:  # Data filter
                if descendants:
                    self._install_filters(descendants, 'DATA', new_flag)
                self._data_handlers.append(
                    partial(self._handle_data, output=output, matcher=matcher,
                            pre_flag=pre_flag, pos_flag=new_flag))
            self._stack.remove(id(html_filter))

    def _start_tag(self, tag, attrs, tag_, matcher, output,
                   pre_flag=None, pos_flag=None):
        if pre_flag and not self._flag_pool.get(pre_flag, False):
            return
        if tag == tag_:
            if matcher(attrs):
                self._flag_pool.update({pos_flag: True})
                if output:
                    attrs = dict(attrs)
                    for item in output:
                        key, name = item[0], item[1]
                        value = attrs.get(key, None)
                        values = self._value_pool.get(name, [])
                        values.append(value)
                        self._value_pool.update({name: values})

    def _end_tag(self, tag, tag_, flag):
        if flag and (tag == tag_):
            self._flag_pool.pop(flag, None)

    def _handle_data(self, data, output, matcher, pre_flag=None, pos_flag=None):
        if pre_flag and not self._flag_pool.get(pre_flag, False):
            return
        if matcher(data):
            self._flag_pool.update({pos_flag: True})
            if output:
                values = self._value_pool.get(output, [])
                values.append(data)
                self._value_pool.update({output: values})

    def handle_starttag(self, tag, attrs):
        for handler in self._starttag_handlers:
            handler(tag, attrs)

    def handle_endtag(self, tag):
        for handler in self._endtag_handlers:
            handler(tag)

    def handle_data(self, data):
        for handler in self._data_handlers:
            handler(data)

    def validate(self):
        for values in self._value_pool.values():
            if not values or values[0] is None:
                return False
        return True

    def dump(self):
        return copy.deepcopy(self._value_pool)