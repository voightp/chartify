import unittest
import uuid
import datetime
import random
from chartify.charts.trace import Trace, TraceData, Trace2D
from chartify.charts.chart_settings import *
from eso_reader.constants import *


class TestChartLayout(unittest.TestCase):
    def setUp(self) -> None:
        n_daily = 8
        n_hourly = 48

        base_date = datetime.datetime.utcnow()
        daily = [base_date + datetime.timedelta(days=i) for i in range(n_daily)]
        hourly = [base_date + datetime.timedelta(hours=i) for i in range(n_hourly)]
        runperiod = [base_date + datetime.timedelta(days=random.randint(100, 400))]

        self.dt0 = TraceData("item-0", uuid.uuid1(), "trace data 0",
                             [random.random() for _ in range(n_hourly)], 5.123, "W",
                             timestamps=hourly, interval=H)
        self.dt1 = TraceData("item-1", uuid.uuid1(), "trace data 1",
                             [random.random() for _ in range(n_hourly)], 5.123, "W",
                             timestamps=hourly, interval=H)
        self.dt2 = TraceData("item-2", uuid.uuid1(), "trace data 2",
                             [random.random() for _ in range(n_daily)], 3.123, "J",
                             timestamps=daily, interval=D)
        self.dt3 = TraceData("item-3", uuid.uuid1(), "trace data 3",
                             random.random(), 3.123, "W",
                             timestamps=runperiod, interval=RP)
        self.dt4 = TraceData("item-4", uuid.uuid1(), "trace data 4",
                             [random.random() for _ in range(n_hourly)], 3.123, "W")
        self.dt5 = TraceData("item-4", uuid.uuid1(), "trace data 5",
                             [random.random() for _ in range(n_hourly)], 3.123, "")

        self.a0 = Axis("x", "hourly")
        self.a1 = Axis("x2", "daily")
        self.a2 = Axis("x3", "monthly")
        self.a3 = Axis("x4", "W")
        self.a4 = Axis("x5", "J")

        self.a0 = Axis("y", "K")
        self.a1 = Axis("y2", "W")
        self.a2 = Axis("y3", "J")
        self.a3 = Axis("y4", "datetime")
        self.a4 = Axis("y5", "hourly")

    def tearDown(self) -> None:
        pass

    def test_trace2d(self):
        t0 = Trace2D("item-1", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        t0.x_ref = self.dt0

        self.assertIs(t0.x_ref, self.dt0)
        self.assertEqual(t0._interval, H)
        self.assertEqual(t0._num_values, 48)

        t0.y_ref = self.dt4
        self.assertIs(t0.y_ref, self.dt4)

        t0.y_ref = self.dt2
        self.assertIs(t0.y_ref, self.dt4)

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
        pass

    def test_create_2d_axis_map(self):
        t0 = Trace2D("item-1", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        t0.x_ref = self.dt0
        t0.y_ref = self.dt4
        t1 = Trace2D("item-1", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        t1.x_ref = self.dt0
        t1.y_ref = self.dt4
        t2 = Trace2D("item-1", uuid.uuid1(), "rgb(10,10,10)", "line", "trace-0")
        t2.x_ref = self.dt4
        t2.y_ref = self.dt0

        traces = [t0, t1, t2]
        create_2d_axis_map(traces)


if __name__ == "__main__":
    unittest.main()
