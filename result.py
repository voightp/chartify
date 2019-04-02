# def add_hourly(self, id, data_row_list, current_interval_data):
#     result = HourlyResult(data_row_list)
#     self.hourly_results[id].append((result, current_interval_data))
#
# def add_daily(self, id, data_row_list, current_interval_data):
#     result = HourlyResult(data_row_list)
#     self.daily_results[id].append((result, current_interval_data))
#
# def add_monthly(self, id, data_row_list, current_interval_data):
#     result = HourlyResult(data_row_list)
#     self.monthly_results[id].append((result, current_interval_data))
#
# def add_runperiod(self, id, data_row_list, current_interval_data):
#     result = HourlyResult(data_row_list)
#     self.runperiod_results[id].append((result, current_interval_data))


# def process_new_env(self, data_row_list):
#     return 1, None
#
# def process_hourly(self, data_row_list):
#     interval = HourlyInterval(data_row_list)
#     return 2, interval
#
# def process_daily(self, data_row_list):
#     interval = DailyInterval(data_row_list)
#     return 3, interval
#
# def process_monthly(self, data_row_list):
#     interval = MonthlyInterval(data_row_list)
#     return 4, interval
#
# def process_runperiod(self, data_row_list):
#     interval = RunperiodInterval(data_row_list)
#     return 5, interval



class HourlyInterval:
    def __init__(self, data):
        self.day_of_simulation = data[0]
        self.month = data[1]
        self.day_of_month = data[2]
        self.dst_indicator = data[3]
        self.hour = data[4]
        self.start_minute = data[5]
        self.end_minute = data[6]
        self.day_type = data[7]


class DailyInterval:
    def __init__(self, data):
        self.day_of_simulation = data[0]
        self.month = data[1]
        self.day_of_month = data[2]
        self.dst_indicator = data[3]
        self.day_type = data[4]


class MonthlyInterval:
    def __init__(self, data):
        self.day_of_simulation = data[0]
        self.month = data[1]


class RunperiodInterval:
    def __init__(self, data):
        self.day_of_simulation = data[0]


class HourlyResult:
    def __init__(self, data):
        self.value = data[0]


class DailyResult:
    def __init__(self, data):
        self.value = data[0]
        self.min_value = data[1]
        self.min_date = (data[2],data[3])
        self.max_value = data[4]
        self.max_date = (data[5], data[6])
        self.interval = data[7]


class MonthlyResult:
    def __init__(self, value, min_value, min_day, min_hour, min_minute, max_value, max_day, max_hour, max_minute,
                 interval):
        self.value = value
        self.min_value = min_value
        self.min_date = (min_day, min_hour, min_minute)
        self.max_value = max_value
        self.max_date = (max_day, max_hour, max_minute)
        self.interval = interval
        # self.number_of_days = number_of_days
        # self.month = month


class RunperiodResult:
    def __init__(self, value, min_value, min_month, min_day, min_hour, min_minute, max_value, max_month, max_day,
                 max_hour, max_minute, interval):
        self.value = value
        self.min_value = min_value
        self.min_date = (min_month, min_day, min_hour, min_minute)
        self.max_value = max_value
        self.max_date = (max_month, max_day, max_hour, max_minute)
        self.interval = interval