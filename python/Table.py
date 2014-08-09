class Table(object):
    def __init__(self, header=None):
        self._width = 0
        self._space = []
        self._header = None
        self._data = []

        if header:
            self.set_header(header)

    def set_header(self, header):
        assert isinstance(header, (tuple, list)), \
            'Invalid headers - Must be list'
        assert len(header) > 0, 'Invalid headers - Must specify columns'
        self._header = header
        self._width = len(self._header)
        self._space = [len(hdr) for hdr in self._header]

    def reset(self):
        self._width = 0
        self._space = []
        self._header = None
        self._data = []

    def add_row(self, data):
        assert isinstance(data, (tuple, list)), 'Invalid data - Must be list'
        if len(data) <= 0:
            return

        new_row = []
        if self._width == 0:
            self._width = len(data)

        # If provided data contains more elements than the existing header
        # then the extra elements will be ignored.
        for i in range(min(len(data), self._width)):
            new_row.append(data[i])
            self._space[i] = max(len(data[i]), self._space[i])
        if len(new_row) < self._width:
            length = len(new_row)
            for i in range(self._width - length):
                new_row.append('')
        self._data.append(new_row)

    def add_rows(self, data):
        assert isinstance(data, (tuple, list)), 'Invalid data - Must be list'
        if not isinstance(data[0], (tuple, list)):
            self.add_row(data)
            return
        for row in data:
            self.add_row(row)

    def populate(self):
        if self._width == 0:
            print('No data available')
            return

        print('\n\n\n')
        bdfmt = '%%%ds' * self._width
        fmt = bdfmt % tuple(-(v + 3) for v in self._space)
        print(fmt % tuple(self._header))
        print('-' * (sum(self._space) + 3 * self._width))
        for row in self._data:
            print(fmt % tuple(row))

    def print2csv(self):
        def print_csv_row(row_data):
            for cell in row_data:
                print('"%s",' % cell,)
            print()

        if self._width == 0:
            print('No data available')
            return

        print_csv_row(self._header)
        for row in self._data:
            print_csv_row(row)