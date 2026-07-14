import unittest
from types import SimpleNamespace

from app.lambda_function import lambda_handler


class LambdaHandlerTests(unittest.TestCase):
    def test_returns_html_page(self):
        response = lambda_handler({}, SimpleNamespace(aws_request_id="test-request"))

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["content-type"], "text/html; charset=utf-8")
        self.assertIn("Ship ideas", response["body"])
        self.assertIn("test-request", response["body"])

    def test_escapes_request_id(self):
        response = lambda_handler({}, SimpleNamespace(aws_request_id="<script>"))
        self.assertNotIn("<script>", response["body"])
        self.assertIn("&lt;script&gt;", response["body"])


if __name__ == "__main__":
    unittest.main()
