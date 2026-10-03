"""Focused data and widget checks for the optional dataset charts."""

import os
from pathlib import Path
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from report_charts import CHART_NAMES, build_report_chart, genre_memberships, heatmap_values


class ReportChartTests(unittest.TestCase):
    def setUp(self):
        self.titles = pd.DataFrame({
            "release_year": [2014, 2015, 2016, 2024],
            "media_type": ["movie", "tv", "movie", "movie"],
            "genres": ["Drama|Drama| Action ", "Drama2", None, "Action"],
            "rating": [8., 6., 4., 9.],
            "global_score": [7., 6.5, 5., 8.],
            "vote_count": [10, 1, 0, 100],
        })
        self.trends = pd.DataFrame({
            "release_year": [2014, 2015, 2014, 2024],
            "media_type": ["movie", "movie", "tv", "movie"],
            "genre": ["Drama", "Drama", "Drama", "Drama"],
            "title_count": [5, 4, 20, 20],
            "mean_genre_score": [7., 9., 6., 10.],
        })
        self.baselines = {"movie": {"C": 6.38}, "tv": {"C": 6.92}}

    def tearDown(self):
        plt.close("all")

    def test_exact_genre_memberships_are_distinct_per_title(self):
        counts = genre_memberships(self.titles)["genre"].value_counts().to_dict()
        self.assertEqual(counts, {"Action": 2, "Drama": 1, "Drama2": 1})

    def test_heatmap_uses_selected_media_and_masks_small_cohorts(self):
        values = heatmap_values(self.trends, "movie")
        self.assertEqual(list(values.columns), list(range(2014, 2024)))
        self.assertEqual(values.loc["Drama", 2014], 7.)
        self.assertTrue(np.isnan(values.loc["Drama", 2015]))
        self.assertTrue(np.isnan(values.loc["Drama", 2016]))

    def test_genre_chart_excludes_out_of_window_title(self):
        fig = build_report_chart(CHART_NAMES[0], self.titles, self.trends, self.baselines)
        self.assertEqual(sorted(p.get_width() for p in fig.axes[0].patches), [1, 1, 1])

    def test_scatter_excludes_zero_votes_and_is_reproducible(self):
        fig = build_report_chart(CHART_NAMES[4], self.titles, self.trends, self.baselines)
        first = fig.axes[0].collections[0].get_offsets().copy()
        repeat = build_report_chart(CHART_NAMES[4], self.titles, self.trends, self.baselines)
        np.testing.assert_array_equal(first, repeat.axes[0].collections[0].get_offsets())
        self.assertEqual(set(first[:, 0]), {1, 10})

    def test_histogram_shows_both_medium_priors(self):
        fig = build_report_chart(CHART_NAMES[2], self.titles, self.trends, self.baselines)
        self.assertEqual([line.get_xdata()[0] for line in fig.axes[0].lines], [6.38, 6.92])

    def test_all_charts_handle_empty_inputs_without_opening_figures(self):
        for name in CHART_NAMES:
            with self.subTest(chart=name):
                result = build_report_chart(name, self.titles.iloc[:0],
                                            self.trends.iloc[:0], self.baselines)
                self.assertIsNone(result)
        self.assertEqual(plt.get_fignums(), [])

    def test_all_chart_types_draw_available_data(self):
        for name in CHART_NAMES:
            with self.subTest(chart=name):
                fig = build_report_chart(name, self.titles, self.trends, self.baselines)
                self.assertIsNotNone(fig)
                fig.canvas.draw()
                plt.close(fig)


class DatasetChartAppTests(unittest.TestCase):
    def test_optional_charts_preserve_rankings_and_existing_tabs(self):
        app_root = Path(__file__).resolve().parents[1]
        previous_cwd = Path.cwd()
        try:
            os.chdir(app_root)
            app = AppTest.from_file(str(app_root / "app.py"), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertEqual([tab.label for tab in app.tabs], ["Overview", "Trends", "Search"])
            initial_rankings = app.dataframe[0].value.copy()
            self.assertTrue(initial_rankings["vote_count"].ge(50).all())
            app.checkbox(key="show_dataset_charts").check().run()
            self.assertFalse(app.exception)
            for name in CHART_NAMES:
                app.selectbox(key="dataset_chart").select(name).run()
                self.assertFalse(app.exception, name)
                pd.testing.assert_frame_equal(initial_rankings, app.dataframe[0].value)
                self.assertEqual(plt.get_fignums(), [])
            app.sidebar.radio[0].set_value("tv").run()
            self.assertFalse(app.exception)
            app.checkbox(key="show_dataset_charts").uncheck().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox), 2)
        finally:
            os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
