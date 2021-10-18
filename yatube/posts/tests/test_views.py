import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Comment, Follow, Group, Post, User
from yatube.settings import POSTS_PER_PAGE


SLUG = 'test-slug'
SECOND_SLUG = 'test-slug-2'
USERNAME = 'auth'
USERNAME2 = 'auth2'
USERNAME3 = 'auth3'
MAIN_PAGE_URL = reverse('posts:main_page')
CREATE_URL = reverse('posts:post_create')
GROUP_URL = reverse('posts:group_post', args=[SLUG])
SECOND_GROUP_URL = reverse(
    'posts:group_post', args=[SECOND_SLUG]
)
PROFILE_URL = reverse('posts:profile', args=[USERNAME])
FOLLOW_PAGE_URL = reverse('posts:follow_index')
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)
PROFILE_FOLLOW = reverse(
    'posts:profile_follow', args=[USERNAME2]
)
PROFILE_UNFOLLOW = reverse(
    'posts:profile_unfollow', args=[USERNAME2]
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.user2 = User.objects.create_user(username=USERNAME2)
        cls.user3 = User.objects.create_user(username=USERNAME3)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
        )
        cls.group_2 = Group.objects.create(
            title='Вторая группа',
            slug=SECOND_SLUG
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=uploaded
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Это комментарий, ура'
        )
        Follow.objects.create(
            author=cls.user,
            user=cls.user2
        )
        cls.URL_POST_EDIT = reverse(
            'posts:post_edit', args=[cls.post.pk]
        )
        cls.URL_POST_DETAIL = reverse(
            'posts:post_detail', args=[cls.post.pk]
        )
        cls.authorized_client = Client()
        cls.authorized_client2 = Client()
        cls.authorized_client3 = Client()
        cls.authorized_client.force_login(PostsViewsTests.user)
        cls.authorized_client2.force_login(PostsViewsTests.user2)
        cls.authorized_client3.force_login(PostsViewsTests.user3)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def test_post_shows_correctly(self):
        urls = [
            MAIN_PAGE_URL,
            GROUP_URL,
            PROFILE_URL,
            PostsViewsTests.URL_POST_DETAIL,
            FOLLOW_PAGE_URL,
        ]
        for url in urls:
            response = PostsViewsTests.authorized_client2.get(url)
            with self.subTest(url=url):
                if url == PostsViewsTests.URL_POST_DETAIL:
                    post = response.context['post']
                else:
                    post = response.context['page_obj'][0]
                    self.assertEqual(len(response.context['page_obj']), 1)
                self.assertEqual(post.text, PostsViewsTests.post.text)
                self.assertEqual(post.author, PostsViewsTests.post.author)
                self.assertEqual(post.group, PostsViewsTests.post.group)
                self.assertEqual(post.image, PostsViewsTests.post.image)

    def test_post_is_not_shown_not_in_its_group(self):
        response = PostsViewsTests.authorized_client.get(SECOND_GROUP_URL)
        self.assertNotIn(PostsViewsTests.post, response.context['page_obj'])

    def test_post_is_not_shown_in_user_not_following(self):
        response = PostsViewsTests.authorized_client3.get(FOLLOW_PAGE_URL)
        self.assertNotIn(PostsViewsTests.post, response.context['page_obj'])

    def test_author_on_profile(self):
        response = PostsViewsTests.authorized_client.get(PROFILE_URL)
        self.assertEqual(PostsViewsTests.user, response.context['author'])

    def test_group_on_group_page(self):
        response = PostsViewsTests.authorized_client.get(GROUP_URL)
        group = response.context['group']
        self.assertEqual(PostsViewsTests.group.slug, group.slug)
        self.assertEqual(PostsViewsTests.group.title, group.title)
        self.assertEqual(PostsViewsTests.group.description, group.description)

    def test_comment_on_url_post_detail(self):
        response = PostsViewsTests.authorized_client.get(
            PostsViewsTests.URL_POST_DETAIL
        )
        self.assertIn(PostsViewsTests.comment, response.context['comments'])

    def test_cashe(self):
        response = PostsViewsTests.authorized_client.get(MAIN_PAGE_URL)
        Post.objects.last().delete()
        self.assertEqual(
            response.content,
            PostsViewsTests.authorized_client.get(MAIN_PAGE_URL).content
        )
        cache.clear()
        self.assertNotEqual(
            response.content,
            PostsViewsTests.authorized_client.get(MAIN_PAGE_URL).content
        )

    def test_user_cant_follow_himself(self):
        PostsViewsTests.authorized_client2.get(PROFILE_FOLLOW)
        self.assertFalse(Follow.objects.filter(
            user=PostsViewsTests.user2, author=PostsViewsTests.user2
        ).exists())

    def test_user_can_follow_author_once(self):
        PostsViewsTests.authorized_client.get(PROFILE_FOLLOW)
        self.assertTrue(Follow.objects.filter(
            user=PostsViewsTests.user, author=PostsViewsTests.user2
        ).exists())

    def test_authorize_follow(self):
        Follow.objects.delete()
        PostsViewsTests.authorized_client3.get(PROFILE_FOLLOW)
        self.assertTrue(Follow.objects.filter(
            user=PostsViewsTests.user3, author=PostsViewsTests.user2
        ).exists())

    def test_authorize_unfollow(self):
        self.assertTrue(Follow.objects.filter(
            user=PostsViewsTests.user, author=PostsViewsTests.user2
        ).exists())
        PostsViewsTests.authorized_client.get(PROFILE_UNFOLLOW)
        self.assertFalse(Follow.objects.filter(
            user=PostsViewsTests.user, author=PostsViewsTests.user2
        ).exists())


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
        )
        for i in range(POSTS_PER_PAGE + 1):
            Post.objects.create(
                text=f'Тестовый пост {i}',
                author=cls.user,
                group=cls.group
            )
        cls.client = Client()
        cls.client.force_login(user=PaginatorViewsTest.user)

    def setUp(self):
        cache.clear()

    def test_first_page_contains_some_records(self):
        names = [
            MAIN_PAGE_URL,
            GROUP_URL,
            PROFILE_URL
        ]
        for name in names:
            with self.subTest(name=name):
                response = PaginatorViewsTest.client.get(name)
                self.assertEqual(
                    len(response.context['page_obj']), POSTS_PER_PAGE
                )

    def test_second_page_contains_other_records(self):
        names = {
            MAIN_PAGE_URL,
            GROUP_URL,
            PROFILE_URL
        }
        for name in names:
            with self.subTest(name=name):
                response = PaginatorViewsTest.client.get(name + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 1)
