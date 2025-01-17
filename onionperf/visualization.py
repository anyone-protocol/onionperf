'''
  OnionPerf
  Authored by Rob Jansen, 2015
  Copyright 2015-2020 The Tor Project
  See LICENSE for licensing information
'''

import matplotlib; matplotlib.use('Agg')  # for systems without X11
from matplotlib.backends.backend_pdf import PdfPages
import time, re
from abc import abstractmethod, ABCMeta
import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters
import seaborn as sns
import datetime
import numpy as np
import logging

class Visualization(object, metaclass=ABCMeta):

    def __init__(self):
        self.datasets = []
        register_matplotlib_converters()

    def add_dataset(self, analyses, label):
        self.datasets.append((analyses, label))

    @abstractmethod
    def plot_all(self, output_prefix):
        pass

class TGenVisualization(Visualization):

    def plot_all(self, output_prefix):
        if len(self.datasets) > 0:
            prefix = output_prefix + '.' if output_prefix is not None else ''
            ts = time.strftime("%Y-%m-%d_%H:%M:%S")
            self.__extract_data_frame()
            self.data.to_csv("{0}onionperf.viz.{1}.csv".format(prefix, ts))
            sns.set_context("paper")
            self.page = PdfPages("{0}onionperf.viz.{1}.pdf".format(prefix, ts))
            self.__plot_firstbyte_ecdf()
            self.__plot_firstbyte_time()
            self.__plot_lastbyte_ecdf()
            self.__plot_lastbyte_box()
            self.__plot_lastbyte_bar()
            self.__plot_lastbyte_time()
            self.__plot_throughput_ecdf()
            self.__plot_downloads_count()
            self.__plot_errors_count()
            self.__plot_errors_time()
            self.page.close()

    def __extract_data_frame(self):
        streams = []
        for (analyses, label) in self.datasets:
            tor_guards_by_client = {}
            for analysis in analyses:
                for client in analysis.get_nodes():
                    known_guards = tor_guards_by_client.setdefault(client, [])
                    if analysis.get_tor_guards(client):
                        for guard in analysis.get_tor_guards(client):
                            if "new_ts" not in guard:
                                _guard = None
                                for g in reversed(known_guards):
                                    if g["fingerprint"] == guard["fingerprint"]:
                                        _guard = g
                                        break
                                if _guard and "dropped_ts" not in _guard:
                                    _guard["dropped_ts"] = guard["dropped_ts"]
                                    continue
                            known_guards.append(guard)
            for analysis in analyses:
                tor_filters = False
                if "filters" in analysis.json_db and "tor/circuits" in analysis.json_db["filters"]:
                    tor_filters = True
                for client in analysis.get_nodes():
                    tor_streams_by_source_port = {}
                    tor_streams = analysis.get_tor_streams(client)
                    fingerprint_pattern = re.compile("\$?([0-9a-fA-F]{40})")
                    for tor_stream in tor_streams.values():
                        if "source" in tor_stream and ":" in tor_stream["source"]:
                            source_port = tor_stream["source"].split(":")[1]
                            tor_streams_by_source_port.setdefault(source_port, []).append(tor_stream)
                    tor_circuits = analysis.get_tor_circuits(client)
                    tgen_streams = analysis.get_tgen_streams(client)
                    tgen_transfers = analysis.get_tgen_transfers(client)
                    while tgen_streams or tgen_transfers:
                        stream = {"time_to_first_byte": None, "time_to_last_byte": None, "error_code": None, "mbps": None}
                        error_code = None
                        source_port = None
                        unix_ts_end = None
                        # Explanation of the math below for computing Mbps: For 1 MiB
                        # downloads we can extract the number of seconds that have elapsed between
                        # receiving bytes 524,288 and 1,048,576, which is a total amount of 524,288
                        # bytes or 4,194,304 bits or 4.194304 megabits.

                        # For 5 MiB downloads we extract the number of seconds that have elapsed between
                        # receiving bytes 4,194,304 and 5,242,880, which is a total amount of 1,048,576
                        # bytes or 8,388,608 bits or 8.388608 megabits. We want the reciprocal of
                        # that value with unit megabits per second.
                        if tgen_streams:
                            stream_id, stream_data = tgen_streams.popitem()
                            stream["id"] = stream_id
                            stream["label"] = label
                            stream["filesize_bytes"] = int(stream_data["stream_info"]["recvsize"])
                            stream["server"] = "onion" if ".anon:" in stream_data["transport_info"]["remote"] else "public"
                            if "time_info" in stream_data:
                                s = stream_data["time_info"]
                                if "usecs-to-first-byte-recv" in s and float(s["usecs-to-first-byte-recv"]) >= 0:
                                    stream["time_to_first_byte"] = float(s["usecs-to-first-byte-recv"])/1000000
                                if "usecs-to-last-byte-recv" in s and float(s["usecs-to-last-byte-recv"]) >= 0:
                                    stream["time_to_last_byte"] = float(s["usecs-to-last-byte-recv"])/1000000
                            if "elapsed_seconds" in stream_data:
                                s = stream_data["elapsed_seconds"]
                                if stream_data["stream_info"]["recvsize"] == "5242880" and "1.0" in s["payload_progress_recv"]:
                                     stream["mbps"] = 8.388608 / (s["payload_progress_recv"]["1.0"] - s["payload_progress_recv"]["0.8"])
                            if "error" in stream_data["stream_info"] and stream_data["stream_info"]["error"] != "NONE":
                                error_code = stream_data["stream_info"]["error"]
                            if "local" in stream_data["transport_info"] and len(stream_data["transport_info"]["local"].split(":")) > 2:
                                source_port = stream_data["transport_info"]["local"].split(":")[2]
                            if "unix_ts_end" in stream_data:
                                unix_ts_end = stream_data["unix_ts_end"]
                            if "unix_ts_start" in stream_data:
                                stream["start"] = datetime.datetime.utcfromtimestamp(stream_data["unix_ts_start"])
                        elif tgen_transfers:
                            transfer_id, transfer_data = tgen_transfers.popitem()
                            stream["id"] = transfer_id
                            stream["label"] = label
                            stream["filesize_bytes"] = transfer_data["filesize_bytes"]
                            stream["server"] = "onion" if ".anon:" in transfer_data["endpoint_remote"] else "public"
                            if "elapsed_seconds" in transfer_data:
                               s = transfer_data["elapsed_seconds"]
                               if "payload_progress" in s:
                                   if transfer_data["filesize_bytes"] == 1048576 and "1.0" in s["payload_progress"]:
                                       stream["mbps"] = 4.194304 / (s["payload_progress"]["1.0"] - s["payload_progress"]["0.5"])
                                   if transfer_data["filesize_bytes"] == 5242880 and "1.0" in s["payload_progress"]:
                                       stream["mbps"] = 8.388608 / (s["payload_progress"]["1.0"] - s["payload_progress"]["0.8"])
                               if "first_byte" in s:
                                   stream["time_to_first_byte"] = s["first_byte"]
                               if "last_byte" in s:
                                   stream["time_to_last_byte"] = s["last_byte"]
                            if "error_code" in transfer_data and transfer_data["error_code"] != "NONE":
                                error_code = transfer_data["error_code"]
                            if "endpoint_local" in transfer_data and len(transfer_data["endpoint_local"].split(":")) > 2:
                                source_port = transfer_data["endpoint_local"].split(":")[2]
                            if "unix_ts_end" in transfer_data:
                                unix_ts_end = transfer_data["unix_ts_end"]
                            if "unix_ts_start" in transfer_data:
                                stream["start"] = datetime.datetime.utcfromtimestamp(transfer_data["unix_ts_start"])
                        tor_circuit = None
                        circuit_id = None
                        if source_port and source_port in tor_streams_by_source_port and unix_ts_end:
                            for tor_stream in tor_streams_by_source_port[source_port]:
                                if abs(unix_ts_end - tor_stream["unix_ts_end"]) < 150.0:
                                    circuit_id = tor_stream["circuit_id"]
                        if circuit_id and str(circuit_id) in tor_circuits:
                            tor_circuit = tor_circuits[circuit_id]
                            guards = []
                            if client in tor_guards_by_client and "current_guards" in tor_circuit:
                                stream["guard_country_codes"] = [d["country"] if "country" in d else "N/A" for d in tor_circuit["current_guards"]]
                                guards = [d["fingerprint"] for d in tor_circuit["current_guards"]]
                                stream["guards"] = int(len(guards))
                            path = tor_circuit["path"]
                            if path:
                                long_name, _ = path[0]
                                fingerprint_match = fingerprint_pattern.match(long_name)
                                if fingerprint_match:
                                    fingerprint = fingerprint_match.group(1).upper()
                                    stream["guard"] = fingerprint
                                    stream["uses_guard"] = fingerprint in guards
                                    try:
                                        stream["guard_index"] = guards.index(fingerprint)
                                    except:
                                        stream["guard_index"] = -1
                        if error_code:
                            if error_code == "PROXY":
                                error_code_parts = ["TOR"]
                            else:
                                error_code_parts = ["TGEN", error_code]
                            if source_port and source_port in tor_streams_by_source_port and unix_ts_end:
                                for tor_stream in tor_streams_by_source_port[source_port]:
                                    if abs(unix_ts_end - tor_stream["unix_ts_end"]) < 150.0:
                                        if "failure_reason_local" in tor_stream:
                                            error_code_parts.append(tor_stream["failure_reason_local"])
                                            if "failure_reason_remote" in tor_stream:
                                                error_code_parts.append(tor_stream["failure_reason_remote"])
                            stream["error_code"] = "/".join(error_code_parts)

                        keep_stream = True
                        if tor_filters:
                           try:
                               if tor_circuit is None or tor_circuit["filtered_out"]:
                                   keep_stream = False
                           except KeyError:
                               pass
                        if keep_stream:
                           streams.append(stream)
        self.data = pd.DataFrame.from_records(streams, index="id")

    def __plot_firstbyte_ecdf(self):
        for server in self.data["server"].unique():
            self.__draw_ecdf(x="time_to_first_byte", hue="label", hue_name="Data set",
                             data=self.data[self.data["server"] == server],
                             title="Time to download first byte from {0} service".format(server),
                             xlabel="Download time (s)", ylabel="Cumulative Fraction")

    def __plot_firstbyte_time(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_timeplot(x="start", y="time_to_first_byte", hue="label", hue_name="Data set",
                                     data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                     title="Time to download first of {0} bytes from {1} service over time".format(bytes, server),
                                     xlabel="Download start time", ylabel="Download time (s)")

    def __plot_lastbyte_ecdf(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_ecdf(x="time_to_last_byte", hue="label", hue_name="Data set",
                                 data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                 title="Time to download last of {0} bytes from {1} service".format(bytes, server),
                                 xlabel="Download time (s)", ylabel="Cumulative Fraction")

    def __plot_lastbyte_box(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_boxplot(x="label", y="time_to_last_byte",
                                    data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                    title="Time to download last of {0} bytes from {1} service".format(bytes, server),
                                    xlabel="Data set", ylabel="Download time (s)")

    def __plot_lastbyte_bar(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_barplot(x="label", y="time_to_last_byte",
                                    data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                    title="Mean time to download last of {0} bytes from {1} service".format(bytes, server),
                                    xlabel="Data set", ylabel="Downloads time (s)")

    def __plot_lastbyte_time(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_timeplot(x="start", y="time_to_last_byte", hue="label", hue_name="Data set",
                                     data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                     title="Time to download last of {0} bytes from {1} service over time".format(bytes, server),
                                     xlabel="Download start time", ylabel="Download time (s)")

    def __plot_throughput_ecdf(self):
        for server in self.data["server"].unique():
            self.__draw_ecdf(x="mbps", hue="label", hue_name="Data set",
                             data=self.data[self.data["server"] == server],
                             title="Throughput when downloading from {0} server".format(server),
                             xlabel="Throughput (Mbps)", ylabel="Cumulative Fraction")

    def __plot_downloads_count(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_countplot(x="label",
                                     data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                     xlabel="Data set", ylabel="Downloads completed (#)",
                                     title="Number of downloads of {0} bytes completed from {1} service".format(bytes, server))

    def __plot_errors_count(self):
        for server in self.data["server"].unique():
            if self.data[self.data["server"] == server]["error_code"].count() > 0:
                self.__draw_countplot(x="error_code", hue="label", hue_name="Data set",
                                      data=self.data[self.data["server"] == server],
                                      xlabel="Error code", ylabel="Downloads failed (#)",
                                      title="Number of downloads failed from {0} service".format(server))

    def __plot_errors_time(self):
        df = self.data
        for server in df["server"].unique():
            if df[df["server"] == server]["error_code"].count() > 0:
                df["start"] = pd.to_datetime(df["start"]).dt.date
                df = df.sort_values(by=["start"])
                self.__draw_stripplot(x="start", y="error_code", hue="label", hue_name="Data set",
                                     data=df[df["server"] == server],
                                     xlabel="Download start time", ylabel="Error code",
                                     title="Downloads failed over time from {0} service".format(server))

    def __draw_ecdf(self, x, hue, hue_name, data, title, xlabel, ylabel):
        data = data.dropna(subset=[x])
        if data.empty:
            return
        p0 = data[x].quantile(q=0.0, interpolation="lower")
        p99 = data[x].quantile(q=0.99, interpolation="higher")
        ranks = data.groupby(hue)[x].rank(pct=True)
        ranks.name = "rank_pct"
        result = pd.concat([data[[hue, x]], ranks], axis=1)
        result = result.append(pd.DataFrame({hue: data[hue].unique(),
                       x: p0 - (p99 - p0) * 0.05, "rank_pct": 0.0}),
                       ignore_index=True, sort=False)
        result = result.append(pd.DataFrame({hue: data[hue].unique(),
                       x: p99 + (p99 - p0) * 0.05, "rank_pct": 1.0}),
                       ignore_index=True, sort=False)
        result = result.rename(columns={hue: hue_name})
        plt.figure()
        g = sns.lineplot(data=result, x=x, y="rank_pct",
                         hue=hue_name, drawstyle="steps-post")
        g.set(title=title, xlabel=xlabel, ylabel=ylabel,
              xlim=(p0 - (p99 - p0) * 0.03, p99 + (p99 - p0) * 0.03))
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_timeplot(self, x, y, hue, hue_name, data, title, xlabel, ylabel):
        data = data.dropna(subset=[y])
        if data.empty:
            return
        plt.figure()
        data = data.rename(columns={hue: hue_name})
        xmin = data[x].min()
        xmax = data[x].max()
        ymin = float(data[y].min())
        ymax = float(data[y].max())
        g = sns.scatterplot(data=data, x=x, y=y, hue=hue_name, alpha=0.5)
        g.set(title=title, xlabel=xlabel, ylabel=ylabel,
              xlim=(xmin - 0.03 * (xmax - xmin), xmax + 0.03 * (xmax - xmin)),
              ylim=(ymin - 0.05 * (ymax - ymin), ymax + 0.05 * (ymax - ymin)))
        plt.xticks(rotation=10)
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_boxplot(self, x, y, data, title, xlabel, ylabel):
        data = data.dropna(subset=[y])
        if data.empty:
            return
        plt.figure()
        g = sns.boxplot(data=data, x=x, y=y, sym="")
        g.set(title=title, xlabel=xlabel, ylabel=ylabel, ylim=(0, None))
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_barplot(self, x, y, data, title, xlabel, ylabel):
        data = data.dropna(subset=[y])
        if data.empty:
            return
        plt.figure()
        g = sns.barplot(data=data, x=x, y=y, ci=None)
        g.set(title=title, xlabel=xlabel, ylabel=ylabel)
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_countplot(self, x, data, title, xlabel, ylabel, hue=None, hue_name=None):
        data = data.dropna(subset=[x])
        if data.empty:
            return
        plt.figure()
        if hue is not None:
            data = data.rename(columns={hue: hue_name})
        g = sns.countplot(data=data.dropna(subset=[x]), x=x, hue=hue_name)
        g.set(xlabel=xlabel, ylabel=ylabel, title=title)
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_stripplot(self, x, y, hue, hue_name, data, title, xlabel, ylabel):
        data = data.dropna(subset=[y])
        if data.empty:
            return
        plt.figure()
        fig, ax = plt.subplots()
        data = data.rename(columns={hue: hue_name})
        if data.empty:
            return
        g = sns.stripplot(data=data, x=x, y=y, hue=hue_name, alpha=0.5)
        g.set(title=title, xlabel=xlabel, ylabel=ylabel)
        plt.xticks(rotation=10)
        sns.despine()
        fig.tight_layout()
        self.page.savefig()
        plt.close()