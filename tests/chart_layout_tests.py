import unittest
import uuid
import datetime
import random
from chartify.charts.trace import Trace, TraceData, Trace2D
from chartify.charts.chart_settings import *
from eso_reader.constants import *


class TestChartLayout(unittest.TestCase):
    def setUp(self) -> None:
        n_monthly = 2
        n_daily = 8
        n_hourly = 48
        n_timestamp = 96

        base_date = datetime.datetime.utcnow()
        timestep = [base_date + datetime.timedelta(minutes=i * 30) for i in range(n_timestamp)]
        hourly = [base_date + datetime.timedelta(hours=i) for i in range(n_hourly)]
        daily = [base_date + datetime.timedelta(days=i) for i in range(n_daily)]
        monthly = [base_date + datetime.timedelta(days=31 * i) for i in range(n_monthly)]
        runperiod = [base_date + datetime.timedelta(days=random.randint(100, 400))]

        # timestamp trace data
        self.ts_dt0 = TraceData("item-0", uuid.uuid1(), "ts-0",
                                [random.random() for _ in range(n_timestamp)],
                                5.123, "W", timestamps=timestep, interval=H)

        # hourly trace data
        self.h_dt0 = TraceData("item-0", uuid.uuid1(), "h-0",
                               [random.random() for _ in range(n_hourly)],
                               5.123, "W", timestamps=hourly, interval=H)
        self.h_dt1 = TraceData("item-0", uuid.uuid1(), "h-1",
                               [random.random() for _ in range(n_hourly)],
                               5.123, "W", timestamps=hourly, interval=H)
        self.h_dt2 = TraceData("item-0", uuid.uuid1(), "h-2",
                               [random.random() for _ in range(n_hourly)],
                               5.123, "kWh", timestamps=hourly, interval=H)
        self.h_dt3 = TraceData("item-0", uuid.uuid1(), "h-3",
                               [random.random() for _ in range(n_hourly)],
                               5.123, "W", timestamps=hourly, interval=H)

        # daily trace data
        self.d_dt0 = TraceData("item-0", uuid.uuid1(), "d-0",
                               [random.random() for _ in range(n_daily)],
                               3.123, "J", timestamps=daily, interval=D)
        self.d_dt1 = TraceData("item-0", uuid.uuid1(), "d-1",
                               [random.random() for _ in range(n_daily)],
                               3.123, "", timestamps=daily, interval=D)

        # monthly trace data
        self.m_dt0 = TraceData("item-0", uuid.uuid1(), "m-0",
                               [random.random() for _ in range(n_monthly)],
                               3.123, "kWh", timestamps=monthly, interval=M)
        self.m_dt1 = TraceData("item-0", uuid.uuid1(), "m-1",
                               [random.random() for _ in range(n_monthly)],
                               3.123, "J", timestamps=monthly, interval=M)

        # runperiod trace data
        self.rp_dt0 = TraceData("item-0", uuid.uuid1(), "rp-0",
                                [random.random()], 3.123, "W",
                                timestamps=runperiod, interval=RP)

        # no interval trace data
        self.ni_dt0 = TraceData("item-0", uuid.uuid1(), "ni-0",
                                [random.random() for _ in range(n_hourly)],
                                1.123, "")
        self.ni_dt1 = TraceData("item-0", uuid.uuid1(), "ni-1",
                                [random.random() for _ in range(n_daily)],
                                7.123, "")
        self.ni_dt2 = TraceData("item-0", uuid.uuid1(), "ni-2",
                                [random.random() for _ in range(n_monthly)],
                                7.123, "")
        self.ni_dt3 = TraceData("item-0", uuid.uuid1(), "ni-3",
                                [random.random() for _ in range(1)],
                                7.123, "")

        # timestamp traces
        self.ts_trace0 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.ts_trace0.x_ref = "datetime"
        self.ts_trace0.y_ref = self.ts_dt0

        # hourly traces
        self.h_trace0 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.h_trace0.x_ref = "datetime"
        self.h_trace0.y_ref = self.h_dt0
        self.h_trace1 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.h_trace1.x_ref = "datetime"
        self.h_trace1.y_ref = self.h_dt1
        self.h_trace2 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.h_trace2.x_ref = self.h_dt2
        self.h_trace2.y_ref = self.h_dt3

        # daily traces
        self.d_trace0 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.d_trace0.x_ref = "datetime"
        self.d_trace0.y_ref = self.d_dt0
        self.d_trace1 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.d_trace1.x_ref = self.d_dt1
        self.d_trace1.y_ref = "datetime"
        self.d_trace2 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.d_trace2.x_ref = self.d_dt1
        self.d_trace2.y_ref = self.d_dt0

        # monthly traces
        self.m_trace0 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.m_trace0.x_ref = "datetime"
        self.m_trace0.y_ref = self.d_dt0
        self.m_trace1 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.m_trace1.x_ref = self.d_dt1
        self.m_trace1.y_ref = "datetime"
        self.m_trace2 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.m_trace2.x_ref = self.d_dt1
        self.m_trace2.y_ref = self.d_dt0

        # runperiod traces
        self.rp_trace0 = Trace2D("item-0", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        self.rp_trace0.x_ref = "datetime"
        self.rp_trace0.y_ref = self.rp_dt0

    def tearDown(self) -> None:
        pass

    def test_trace2d(self):
        t0 = Trace2D("item-1", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        t0.x_ref = self.h_dt0

        self.assertIs(t0.x_ref, self.h_dt0)
        self.assertEqual(t0._interval, H)
        self.assertEqual(t0._num_values, 48)

        t0.y_ref = self.h_dt1
        self.assertIs(t0.y_ref, self.h_dt1)

        t0.y_ref = self.ts_dt0
        self.assertIs(t0.y_ref, self.h_dt1)

    def test_gen_ref_matrix(self):
        m = gen_ref_matrix(0, 3, True)
        self.assertEqual(m, [[]])

        m = gen_ref_matrix(1, 3, True)
        self.assertEqual(m, [[0]])

        m = gen_ref_matrix(5, 3, True)
        self.assertEqual(m, [[0, 1, 2], [3, 4]])

        m = gen_ref_matrix(4, 3, True)
        self.assertEqual(m, [[0, 1], [2, 3]])

        m = gen_ref_matrix(4, 3, False)
        self.assertEqual(m, [[0, 1, 2], [3]])

    def test_dom_gen(self):
        gen = dom_gen(3, 0.1)

        d0 = next(gen)
        d1 = next(gen)
        d2 = next(gen)

        self.assertAlmostEqual(d0[0], 0)
        self.assertAlmostEqual(d0[1], 0.26666, 4)
        self.assertAlmostEqual(d1[0], 0.36666, 4)
        self.assertAlmostEqual(d1[1], 0.63333, 4)
        self.assertAlmostEqual(d2[0], 0.733333, 4)
        self.assertAlmostEqual(d2[1], 1)

        with self.assertRaises(StopIteration):
            next(gen)

    def test_gen_domain_vectors(self):
        x_domains, y_domains = gen_domain_vectors(5, gap=0.1,
                                                  max_columns=2, square=False)
        res_xs = [[0, 0.45], [0.55, 1.0], [0, 0.45], [0.55, 1.0], [0, 1.0]]
        res_ys = [[0, 0.266666], [0, 0.266666], [0.366666, 0.633333],
                  [0.3666667, 0.6333333], [0.7333333, 1.0]]

        for x, res_x in zip(x_domains, res_xs):
            for ix, ires_x in zip(x, res_x):
                self.assertAlmostEqual(ix, ires_x, 4)

        for y, res_y in zip(y_domains, res_ys):
            for iy, ires_y in zip(y, res_y):
                self.assertAlmostEqual(iy, ires_y, 4)

        x_domains, y_domains = gen_domain_vectors(4, gap=0.1,
                                                  max_columns=2, square=True)

        res_xs = [[0, 0.45], [0.55, 1.0], [0, 0.45], [0.55, 1.0]]
        res_ys = [[0, 0.45], [0, 0.45], [0.55, 1.0], [0.55, 1.0]]

        for x, res_x in zip(x_domains, res_xs):
            for ix, ires_x in zip(x, res_x):
                self.assertAlmostEqual(ix, ires_x, 4)

        for y, res_y in zip(y_domains, res_ys):
            for iy, ires_y in zip(y, res_y):
                self.assertAlmostEqual(iy, ires_y, 4)

        x_domains, y_domains = gen_domain_vectors(4, gap=0.1,
                                                  max_columns=3, square=False)

        res_xs = [[0, 0.266666], [0.3666667, 0.6333333], [0.733333, 1.0], [0, 1.0]]
        res_ys = [[0, 0.45], [0, 0.45], [0, 0.45], [0.55, 1.0]]

        for x, res_x in zip(x_domains, res_xs):
            for ix, ires_x in zip(x, res_x):
                self.assertAlmostEqual(ix, ires_x, 4)

        for y, res_y in zip(y_domains, res_ys):
            for iy, ires_y in zip(y, res_y):
                self.assertAlmostEqual(iy, ires_y, 4)

    def test_set_shared_x_positions(self):
        a = Axis("x", "W")
        for i in range(2, 6):
            a.add_child(Axis(f"x{i}", f"foo{i}", visible=(i % 2 == 0)))

        y_domain = [0.3, 0.7]
        increment = 0.02

        y_bottom, y_top = set_shared_x_positions(a, y_domain, increment)
        self.assertAlmostEqual(y_bottom, 0.34, 5)
        self.assertEqual(y_top, 0.7)

        pos = 0.3
        for ch in a.children[::-1]:
            if ch.visible:
                self.assertEqual(ch.anchor, "free")
                self.assertAlmostEqual(ch.position, pos, 4)
                pos += increment
            else:
                self.assertIsNone(ch.anchor)
                self.assertIsNone(ch.position)

    def test_set_shared_y_positions(self):
        a = Axis("y", "W")
        for i in range(2, 7):
            a.add_child(Axis(f"y{i}", f"foo{i}", visible=(i % 2 == 0)))

        x_domain = [0.3, 0.7]
        increment = 0.02

        x_left, x_right = set_shared_y_positions(a, x_domain, increment)
        self.assertAlmostEqual(x_left, 0.32, 5)
        self.assertAlmostEqual(x_right, 0.68, 5)

        left, right = x_domain[0], x_domain[1]
        for i, ch in enumerate(a.visible_children[::-1]):
            self.assertEqual(ch.anchor, "free")
            if i % 2 == 0:
                self.assertAlmostEqual(ch.position, right, 4)
                self.assertEqual(ch.side, "right")
                right -= increment
            else:
                self.assertAlmostEqual(ch.position, left, 4)
                self.assertEqual(ch.side, "left")
                left += increment

        for i, ch in enumerate(a.hidden_children[::-1]):
            self.assertIsNone(ch.anchor)
            self.assertIsNone(ch.position)

        # reduce one visible and one invisible child
        a.children.pop(0)
        a.children.pop(0)

        x_left, x_right = set_shared_y_positions(a, x_domain, increment)
        self.assertAlmostEqual(x_left, 0.32, 5)
        self.assertAlmostEqual(x_right, 0.7, 5)

        left, right = x_domain[0], x_domain[1]
        for i, ch in enumerate(a.visible_children[::-1]):
            self.assertEqual(ch.anchor, "free")
            if i % 2 == 1:
                self.assertAlmostEqual(ch.position, right, 4)
                self.assertEqual(ch.side, "right")
                right -= increment
            else:
                self.assertAlmostEqual(ch.position, left, 4)
                self.assertEqual(ch.side, "left")
                left += increment

        for i, ch in enumerate(a.hidden_children[::-1]):
            self.assertIsNone(ch.anchor)
            self.assertIsNone(ch.position)

    def test_assign_domains(self):
        x0 = Axis("x", "hourly")
        x0.add_child(Axis("x2", "kg"))
        x0.add_child(Axis("x3", "daily", visible=False))
        x0.add_child(Axis("x4", "monthly", visible=False))

        y0 = Axis("y", "C")
        y0.add_child(Axis("y2", "W"))
        y0.add_child(Axis("y3", "J"))
        y0.add_child(Axis("y4", ""))

        x1 = Axis("x5", "m3")
        x1.add_child(Axis("x6", "kg"))
        x1.add_child(Axis("x7", "daily", visible=False))
        x1.add_child(Axis("x8", "monthly", visible=False))

        y1 = Axis("y", "C")
        y1.add_child(Axis("y2", "W"))
        y1.add_child(Axis("y3", "J"))
        y1.add_child(Axis("y4", ""))

        y2 = Axis("y5", "hourly")
        y2.add_child(Axis("y6", "daily", visible=False))
        y2.add_child(Axis("y6", "daily", visible=False))

        y1.add_child(y2)

        assign_domains([(x0, y0)], True, True)

        print(x0)
        print(y0)

        for ch in x0.children:
            print(ch)

        for ch in y0.children:
            print(ch)

    def test_create_2d_axis_map(self):
        traces = [
            self.ts_trace0,
            self.h_trace0,
            self.h_trace1,
            self.h_trace2,
            self.d_trace0,
            self.d_trace1,
            self.d_trace2,
            self.m_trace0,
            self.m_trace1,
        ]
        mp1 = create_2d_axis_map(traces)


if __name__ == "__main__":
    unittest.main()
