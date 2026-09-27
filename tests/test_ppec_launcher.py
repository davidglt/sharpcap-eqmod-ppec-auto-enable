#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created: 2026-09-27
# Author: David González López-Tercero <davidglt@dragonit.es>
# SPDX-FileCopyrightText: 2026 David González López-Tercero <davidglt@dragonit.es>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for PPEC launcher locking and worker supervision."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


class FakeThreadStart:
    def __init__(self, callback):
        self.callback = callback


class FakeThread:
    def __init__(self, _thread_start):
        self.IsBackground = False
        self.ApartmentState = None

    def Start(self):
        pass


class PpecLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        threading_module = types.ModuleType("System.Threading")
        threading_module.AbandonedMutexException = type(
            "AbandonedMutexException", (Exception,), {}
        )
        threading_module.ApartmentState = types.SimpleNamespace(STA="STA")
        threading_module.Mutex = mock.Mock()
        threading_module.Thread = FakeThread
        threading_module.ThreadStart = FakeThreadStart
        system_module = types.ModuleType("System")
        system_module.__path__ = []
        fake_clr = types.SimpleNamespace(AddReference=mock.Mock())
        path = Path(__file__).resolve().parents[1] / "ppec_auto_enable.py"
        spec = importlib.util.spec_from_file_location("ppec_auto_enable_test", path)
        cls.launcher = importlib.util.module_from_spec(spec)
        cls.launcher.clr = fake_clr
        with mock.patch.dict(
            sys.modules,
            {
                "System": system_module,
                "System.Threading": threading_module,
            },
        ):
            spec.loader.exec_module(cls.launcher)

    def run_launcher(self, exit_code=0, lock_acquired=True):
        mutex = mock.Mock()
        mutex.WaitOne.return_value = lock_acquired
        process = mock.Mock(pid=1234)
        process.wait.return_value = exit_code
        self.launcher.Mutex = mock.Mock(return_value=mutex)
        self.launcher.SharpCap = mock.Mock()
        self.launcher.SharpCap.Mounts.SelectedMount = types.SimpleNamespace(
            Name="Test Mount",
            Tracking=True,
        )

        with (
            mock.patch.object(self.launcher.os.path, "exists", return_value=True),
            mock.patch.object(
                self.launcher.subprocess,
                "Popen",
                return_value=process,
            ) as popen,
            mock.patch.object(self.launcher, "info") as info,
            mock.patch.object(self.launcher, "error") as error,
        ):
            self.launcher.enable_ppec_when_ready()

        return mutex, process, popen, info, error

    def test_active_launcher_holds_mutex_until_worker_finishes(self):
        mutex, process, popen, info, error = self.run_launcher()

        mutex.WaitOne.assert_called_once_with(0)
        mutex.ReleaseMutex.assert_called_once()
        mutex.Close.assert_called_once()
        process.wait.assert_called_once_with()
        popen.assert_called_once()
        info.assert_any_call("Worker completed successfully (exit code 0).")
        error.assert_not_called()

    def test_second_launcher_skips_when_mutex_is_already_held(self):
        mutex, process, popen, info, error = self.run_launcher(lock_acquired=False)

        mutex.ReleaseMutex.assert_not_called()
        mutex.Close.assert_called_once()
        process.wait.assert_not_called()
        popen.assert_not_called()
        info.assert_any_call("Another PPEC auto-enable instance is already active; skipping.")
        error.assert_not_called()

    def test_worker_failure_is_reported_to_sharpcap(self):
        _, _, _, info, error = self.run_launcher(exit_code=1)

        info.assert_any_call("Worker launched (PID 1234).")
        error.assert_any_call("Worker failed with exit code 1.")


if __name__ == "__main__":
    unittest.main()
