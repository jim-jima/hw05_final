from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from ..models import Follow, Group, Post, User

SLUG = 'test-slug'
USERNAME = 'auth'
USERNAME2 = 'auth2'
USERNAME3 = 'auth3'
MAIN_PAGE_URL = reverse('posts:main_page')
CREATE_URL = reverse('posts:post_create')
GROUP_URL = reverse('posts:group_post', args=[SLUG])
PROFILE_URL = reverse('posts:profile', args=[USERNAME2])
UNEXISTING_URL = '/unexisting/'
LOGIN_URL = reverse('users:login')
FOLLOW_INDEX = reverse('posts:follow_index')
PROFILE_FOLLOW = reverse(
    'posts:profile_follow', args=[USERNAME2]
)
PROFILE_UNFOLLOW = reverse(
    'posts:profile_unfollow', args=[USERNAME2]
)


class PostUrlsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group
        )
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.second_authorized_user = User.objects.create_user(
            username=USERNAME2
        )
        cls.second_authorized_client = Client()
        cls.second_authorized_client.force_login(
            cls.second_authorized_user
        )
        cls.third_authorized_user = User.objects.create_user(
            username=USERNAME3
        )
        cls.third_authorized_client = Client()
        cls.third_authorized_client.force_login(
            cls.third_authorized_user
        )
        Follow.objects.create(
            user=cls.user,
            author=cls.second_authorized_user
        )
        cls.POST_URL = reverse(
            'posts:post_detail', args=[cls.post.pk]
        )
        cls.EDIT_URL = reverse(
            'posts:post_edit', args=[cls.post.pk]
        )
        cls.COMMENT_URL = reverse(
            'posts:add_comment', args=[cls.post.pk]
        )

    def setUp(self):
        cache.clear()

    def test_status_codes(self):
        cases = (
            (MAIN_PAGE_URL, PostUrlsTest.guest_client, 200),
            (GROUP_URL, PostUrlsTest.guest_client, 200),
            (PROFILE_URL, PostUrlsTest.guest_client, 200),
            (PostUrlsTest.POST_URL, PostUrlsTest.guest_client, 200),
            (UNEXISTING_URL, PostUrlsTest.guest_client, 404),
            (PostUrlsTest.EDIT_URL, PostUrlsTest.authorized_client, 200),
            (CREATE_URL, PostUrlsTest.authorized_client, 200),
            (PostUrlsTest.EDIT_URL, PostUrlsTest.guest_client, 302),
            (
                PostUrlsTest.EDIT_URL,
                PostUrlsTest.second_authorized_client, 302
            ),
            (CREATE_URL, PostUrlsTest.guest_client, 302),
            (PostUrlsTest.COMMENT_URL, PostUrlsTest.authorized_client, 302),
            (FOLLOW_INDEX, PostUrlsTest.authorized_client, 200),
            (PROFILE_FOLLOW, PostUrlsTest.third_authorized_client, 302),
            (PROFILE_UNFOLLOW, PostUrlsTest.authorized_client, 302),
        )

        for url, client, status in cases:
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, status)

    def test_redirects(self):
        cases = (
            (
                PostUrlsTest.EDIT_URL, PostUrlsTest.guest_client,
                f'{LOGIN_URL}?next={PostUrlsTest.EDIT_URL}'
            ),
            (
                CREATE_URL, PostUrlsTest.guest_client,
                f'{LOGIN_URL}?next={CREATE_URL}'
            ),
            (
                PostUrlsTest.EDIT_URL, PostUrlsTest.second_authorized_client,
                PostUrlsTest.POST_URL,
            ),
            (
                PostUrlsTest.COMMENT_URL, PostUrlsTest.authorized_client,
                PostUrlsTest.POST_URL
            ),
            (
                PROFILE_FOLLOW, PostUrlsTest.third_authorized_client,
                PROFILE_URL
            ),
            (
                PROFILE_UNFOLLOW, PostUrlsTest.third_authorized_client,
                PROFILE_URL
            )
        )
        for url, client, redirect in cases:
            with self.subTest(url=url):
                self.assertRedirects(
                    client.get(url, follow=True), redirect
                )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            MAIN_PAGE_URL: 'posts/index.html',
            GROUP_URL: 'posts/group_list.html',
            PROFILE_URL: 'posts/profile.html',
            PostUrlsTest.POST_URL: 'posts/post_detail.html',
            PostUrlsTest.EDIT_URL: 'posts/create_post.html',
            CREATE_URL: 'posts/create_post.html',
            FOLLOW_INDEX: 'posts/follow.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                self.assertTemplateUsed(
                    PostUrlsTest.authorized_client.get(adress), template
                )
