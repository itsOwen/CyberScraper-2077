import unittest

from main import render_message


class RenderMessageTests(unittest.TestCase):
    def test_user_html_is_escaped(self):
        rendered = render_message("user", '<img src=x onerror="alert(1)">', "app/icons/man.png")
        self.assertNotIn("<img src=x", rendered)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", rendered)


if __name__ == "__main__":
    unittest.main()
