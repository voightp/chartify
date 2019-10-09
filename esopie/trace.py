class RawTrace:
    def __init__(self, info_tup, values, total_value, timestamp, color):
        self.file_name = info_tup[0]
        self.interval = info_tup[1]
        self.key = info_tup[2]
        self.variable = info_tup[3]
        self.units = info_tup[4]
        self.values = values
        self.total_value = total_value
        self.timestamp = timestamp
        self.color = color

    @property
    def js_timestamp(self):
        return [ts * 1000 for ts in self.timestamp]

    @property
    def name(self):
        return f"{self.interval} | {self.file_name}" \
            f" | {self.key} | {self.variable} | {self.units}"

    def as_scatter(self):
        pass

    def as_line(self):
        pass

    def as_bubble(self):
        pass

    def as_bar(self):
        pass

    def as_box(self):
        pass

    def as_hist(self):
        pass

    def as_pie(self):
        pass
