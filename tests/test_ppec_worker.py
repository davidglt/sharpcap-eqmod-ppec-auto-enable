import unittest
from unittest import mock

import ppec_worker


class PpecWorkerTests(unittest.TestCase):
    def test_already_enabled_mount_is_left_unchanged(self):
        scope = mock.Mock()
        scope.CommandString.return_value = ppec_worker.PPEC_ON_RESPONSE

        with mock.patch.object(ppec_worker.time, "sleep") as sleep:
            self.assertTrue(ppec_worker.ensure_ppec_enabled(scope))

        scope.CommandString.assert_called_once_with(">:q1010000", False)
        sleep.assert_not_called()

    def test_enable_is_sent_only_after_confirmed_off_and_then_confirmed_on(self):
        scope = mock.Mock()
        scope.CommandString.side_effect = [
            ppec_worker.PPEC_OFF_RESPONSE,
            "=\r",
            ppec_worker.PPEC_ON_RESPONSE,
        ]

        with mock.patch.object(ppec_worker.time, "sleep") as sleep:
            self.assertTrue(ppec_worker.ensure_ppec_enabled(scope))

        self.assertEqual(
            [call.args for call in scope.CommandString.call_args_list],
            [
                (">:q1010000", False),
                (">:W1020000", False),
                (">:q1010000", False),
            ],
        )
        sleep.assert_called_once_with(2)

    def test_unknown_or_failed_initial_status_does_not_enable_ppec(self):
        for response in ("unexpected response\r", OSError("COM unavailable")):
            with self.subTest(response=response):
                scope = mock.Mock()
                if isinstance(response, Exception):
                    scope.CommandString.side_effect = response
                else:
                    scope.CommandString.return_value = response

                self.assertFalse(ppec_worker.ensure_ppec_enabled(scope))
                scope.CommandString.assert_called_once_with(
                    ">:q1010000",
                    False,
                )

    def test_unconfirmed_activation_fails(self):
        scope = mock.Mock()
        scope.CommandString.side_effect = [
            ppec_worker.PPEC_OFF_RESPONSE,
            "=\r",
            ppec_worker.PPEC_OFF_RESPONSE,
        ]

        with mock.patch.object(ppec_worker.time, "sleep"):
            self.assertFalse(ppec_worker.ensure_ppec_enabled(scope))

        self.assertEqual(scope.CommandString.call_count, 3)


if __name__ == "__main__":
    unittest.main()
