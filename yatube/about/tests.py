from django.test import Client, TestCase


class StaticURLTests(TestCase):

    def setUp(self):
        self.guest_client = Client()

    def test_urls_status_code(self):
        urls_status_code = {
            200: ['/about/author/', '/about/tech/']
        }

        for status, urls in urls_status_code.items():
            for url in urls:
                with self.subTest(url=url):
                    response = self.guest_client.get(url)
                    self.assertEqual(response.status_code, status)
