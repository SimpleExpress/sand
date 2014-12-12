import csv


class FixedColumnTable(object):
    def __init__(self, header=None):
        self.__width = 0
        self.__header = header
        self.__space = []
        self.__data = []

        if header:
            self.set_header(header)

    def set_header(self, header):
        assert isinstance(header, (tuple, list)), \
            'Invalid headers - Must be list'
        assert len(header) > 0, 'Invalid headers - Must specify columns'
        self.__header = [str(v) if v else '' for v in header]
        self.__width = len(self.__header)
        self.__space = [len(hdr) for hdr in self.__header]

    def reset(self):
        self.__width = 0
        self.__header = None
        self.__space.clear()
        self.__data.clear()

    def add_row(self, data):
        assert isinstance(data, (tuple, list)), 'Invalid data - Must be list'
        if len(data) <= 0:
            return

        new_row = []
        if self.__width == 0:
            self.__width = len(data)

        # If provided data contains more elements than the existing header
        # then the extra elements will be ignored.
        for i in range(min(len(data), self.__width)):
            cell = data[i]
            new_row.append(cell)
            self.__space[i] = max(len(str(cell)) if cell else 0,
                                  self.__space[i])
        if len(new_row) < self.__width:
            length = len(new_row)
            for i in range(self.__width - length):
                new_row.append(None)
        self.__data.append(new_row)

    def add_rows(self, data):
        assert isinstance(data, (tuple, list)), 'Invalid data - Must be list'
        if not isinstance(data[0], (tuple, list)):
            self.add_row(data)
            return
        for row in data:
            self.add_row(row)

    def populate(self):
        if self.__width == 0:
            return

        print('\n\n\n')
        pre_fmt = '%%%ds' * self.__width
        fmt = pre_fmt % tuple(-(v + 3) for v in self.__space)
        if self.__header:
            print(fmt % tuple(self.__header))
            print('-' * (sum(self.__space) + 3 * self.__width))
        for row in self.__data:
            cleaned = [str(v) if v else '' for v in row]
            print(fmt % tuple(cleaned))

    def export2csv(self, path, append=False):
        """
        export the table to a csv file, note that the object will be represented
        as string by calling str method
        :param path: the file path for exporting
        :param append: indicates whether to append or override
        :return: None
        """
        def clean(raw_list):
            for i in range(len(raw_list)):
                raw_list[i] = str(raw_list[i]) if raw_list[i] else ''
            return raw_list

        mode = 'w' if not append else 'a'
        with open(path, mode, newline='') as fh:
            if self.__width == 0:
                return

            writer = csv.writer(fh, 'unix')
            if append:
                writer.writerow(['APPENDED TABLE', ])
            if self.__header:
                writer.writerow(self.__header)
            for row in self.__data:
                row = clean(row)
                writer.writerow(row)

    @classmethod
    def loadfromcsv(cls, path):
        with open(path, 'r', newline='') as fh:
            inst = cls()

            dialect = csv.Sniffer().sniff(fh.read(1024))
            fh.seek(0)
            reader = csv.reader(fh, dialect)

            header = next(reader)
            inst.set_header(header)
            for row in reader:
                inst.add_row(row)

            return inst


class ExtensibleColumnTable(object):
    def __init__(self):
        self.__header = []
        self.__data = []
        self.__table = FixedColumnTable()
        self.__wrapped = False

    def reset(self):
        self.__header.clear()
        self.__data.clear()
        self.__table.reset()
        self.__wrapped = False

    def add(self, zipped_record):
        if not zipped_record:
            return
        assert isinstance(zipped_record, (tuple, list)), \
            'Each record MUST be a list'
        assert isinstance(zipped_record[0], (tuple, list)), \
            'Each value MUST be zipped, i.e. in the format of (k, v)'

        if not self.__header:
            record = []
        else:
            record = [None for _ in range(len(self.__header))]

        for k, v in zipped_record:
            if not k:
                self.add(('NO_COLUMN_NAME_ASSIGNED', v))
            if str(k) in self.__header:
                index = self.__header.index(k)
                record[index] = v
            else:
                self.__header.append(str(k))
                record.append(v)
        self.__data.append(tuple(record))

    def __wrap_into_fixed_column(self):
        self.__table.reset()
        self.__table.set_header(self.__header)
        self.__table.add_rows(self.__data)
        self.__wrapped = True

    def populate(self):
        if not self.__header or not self.__data:
            return

        if not self.__wrapped:
            self.__wrap_into_fixed_column()
        self.__table.populate()

    def export2csv(self, path, append=False):
        if not self.__wrapped:
            self.__wrap_into_fixed_column()
        self.__table.export2csv(path, append)
