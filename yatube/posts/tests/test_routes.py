from django.test import TestCase
from django.urls import reverse

from ..models import Post, User

SLUG = 'test-slug'
USERNAME = 'auth'


class RoutesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user
        )

    def test_urls_rotes(self):
        cases = (
            ('main_page', [], '/'),
            ('post_create', [], '/create/'),
            ('group_post', [SLUG], f'/group/{SLUG}/'),
            ('profile', [USERNAME], f'/profile/{USERNAME}/'),
            (
                'post_detail', [RoutesTest.post.pk],
                f'/posts/{RoutesTest.post.pk}/'
            ),
            (
                'post_edit', [RoutesTest.post.pk],
                f'/posts/{RoutesTest.post.pk}/edit/'
            ),
            ('follow_index', [], '/follow/'),
            ('profile_follow', [USERNAME], f'/profile/{USERNAME}/follow/'),
            ('profile_unfollow', [USERNAME], f'/profile/{USERNAME}/unfollow/'),
            ('add_comment',[RoutesTest.post.pk], f'/posts/{RoutesTest.post.pk}/comment/')
        )
        for url_route, args, url in cases:
            with self.subTest(url=url):
                self.assertEqual(reverse(f'posts:{url_route}', args=args), url)
