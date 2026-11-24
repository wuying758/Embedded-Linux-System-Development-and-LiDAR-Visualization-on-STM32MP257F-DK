import os
import subprocess
import unittest


PROGRAM = os.environ.get("HELLO_MENU_BINARY", "/tmp/hello-menu-host")


class SerialMenuTests(unittest.TestCase):
    def run_menu(self, commands):
        result = subprocess.run(
            [PROGRAM], input=commands, text=True, capture_output=True, timeout=15
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_zero_returns_to_shell_after_showing_greeting(self):
        output = self.run_menu("0\n")
        self.assertIn("hello world", output.lower())
        self.assertIn("Select: ", output)
        self.assertIn("Returning to shell.", output)

    def test_kernel_option_reports_the_running_kernel(self):
        output = self.run_menu("2\n0\n")
        self.assertIn("Kernel: " + os.uname().release, output)
        self.assertGreaterEqual(output.count("Select: "), 2)

    def test_echo_option_accepts_a_line_with_spaces(self):
        output = self.run_menu("3\nHello from the serial terminal\n0\n")
        self.assertIn("Echo: Hello from the serial terminal", output)
        self.assertIn("Returning to shell.", output)

    def test_invalid_selection_keeps_the_menu_usable(self):
        output = self.run_menu("9\n0\n")
        self.assertIn("Invalid selection", output)
        self.assertIn("Returning to shell.", output)

    def test_end_of_input_exits_without_hanging(self):
        self.run_menu("")

    def test_long_text_does_not_become_extra_menu_commands(self):
        output = self.run_menu("3\n" + "x" * 600 + "\n0\n")
        self.assertIn("Echo: xxx", output)
        self.assertNotIn("Invalid selection", output)
        self.assertIn("Returning to shell.", output)


if __name__ == "__main__":
    unittest.main()
