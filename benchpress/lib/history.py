#!/usr/bin/env python3

import json
import logging
import os

from .metrics import Metrics

logger = logging.getLogger(__name__)


class HistoryEntry(object):
    """Results from a historical run of a job

    Attributes:
        job_name (str): name of the job
        timestamp (str): time of the run (format: YYYY-MM-DDTHH:MM:SS)
        metrics (Metrics): run's exported metrics
        config (dict): dict of job config at run time
    """
    def __init__(self, record):
        """Create a HistoryEntry from saved dictionary output.

        Args:
            record (dict): saved run dictionary
        """
        self.job_name = record['job']
        self.timestamp = record['timestamp']
        self.config = record['config']
        self.metrics = Metrics(record['metrics'])


class History(object):
    """Interface to save/load benchmark results to/from disk.
    Benchmark results will be saved at paths like follows:
        <path>/<job_name>/<timestamp>.json
    """

    def __init__(self, path):
        """Create a History instance which uses the specified directory

        Args:
            path (str): path to directory to store logs
        """
        self.path = path

    def load_historical_results(self, job):
        """Load all results from a specific job.

        Args:
            job (BenchmarkJob): job to load results for

        Returns:
            list of HistoryEntry: historical entries sorted most recent first.
        """
        results = []

        job_name = job.name.replace(' ', '_')
        rootdir = os.path.join(self.path, job_name)
        for directory, _, files in os.walk(rootdir):
            for f in files:
                with open(os.path.join(directory, f), 'r') as record:
                    record = json.load(record)
                    try:
                        entry = HistoryEntry(record)
                        results.append(entry)
                    except KeyError as e:
                        logger.error('Invalid entry format (missing {})'
                                     .format(e))
                        raise e

        # sort by most recent first
        return sorted(results, key=lambda r: r.timestamp, reverse=True)

    def is_job_config_consistent(self, job):
        """Check if all historical runs of a job had the same config.
        This is used as a basic sanity check, as jobs changing configs is likely
        change the behavior of the test and make interpreting results confusing.

        Args:
            job (BenchmarkJob): job to verify
        """
        history = self.load_historical_results(job)

        for entry in history:
            if entry.config != job.config:
                return False

        return True

    def save_job_result(self, job, metrics, time):
        """Save result of a job run to disk.
        Path is as follows:
            <base path>/<job_name>/<timestamp>.json

        Args:
            job (BenchmarkJob): job that was run
            metrics (Metrics): results
            time (datetime.datetime): start time of the benchmark
        """
        job_name = job.name.replace(' ', '_')
        time = time.strftime('%Y-%m-%dT%H:%M:%S')

        data = {
            'job': job.name,
            'timestamp': time,
            'metrics': metrics.metrics(),
            'config': job.config,
        }

        directory = os.path.join(self.path, job_name)
        os.makedirs(directory, exist_ok=True)

        path = os.path.join(directory, time) + '.json'

        with open(path, 'w') as f:
            json.dump(data, f, sort_keys=True, indent=2)
