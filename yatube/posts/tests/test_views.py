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
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=f'{settings.UPLOAD_TO}{cls.uploaded.name}'
        )
        cls.post2 = Post.objects.create(
            text='Ещё тестовый пост, ура!',
            author=cls.user2
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Это комментарий, ура'
        )
        Follow.objects.create(
            author=cls.user2,
            user=cls.user
        )
        cls.URL_POST_EDIT = reverse(
            'posts:post_edit', args=[cls.post.pk]
        )
        cls.URL_POST_DETAIL = reverse(
            'posts:post_detail', args=[cls.post.pk]
        )
        cls.COMMENT_URL = reverse(
            'posts:add_comment', args=[cls.post.pk]
        )
        cls.PROFILE_FOLLOW = reverse(
            'posts:profile_follow', args=[cls.user2]
        )
        cls.PROFILE_UNFOLLOW = reverse(
            'posts:profile_unfollow', args=[cls.user2]
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client3 = Client()
        self.authorized_client.force_login(PostsViewsTests.user)
        self.authorized_client3.force_login(PostsViewsTests.user3)

    def test_post_shows_correctly(self):
        urls = [
            MAIN_PAGE_URL,
            GROUP_URL,
            PROFILE_URL,
            PostsViewsTests.URL_POST_DETAIL,
        ]
        for url in urls:
            response = self.authorized_client.get(url)
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

    def test_follow_post_shows_correctly(self):
        post = self.authorized_client.get(
            FOLLOW_PAGE_URL
        ).context['page_obj'][0]
        self.assertEqual(post.text, PostsViewsTests.post2.text)
        self.assertEqual(post.author, PostsViewsTests.post2.author)

    def test_post_is_not_shown_not_in_its_group(self):
        response = self.authorized_client.get(SECOND_GROUP_URL)
        self.assertNotIn(PostsViewsTests.post, response.context['page_obj'])

    def test_post_is_not_shown_in_user_not_following(self):
        response = self.authorized_client3.get(FOLLOW_PAGE_URL)
        self.assertNotIn(PostsViewsTests.post, response.context['page_obj'])

    def test_author_on_profile(self):
        response = self.authorized_client.get(PROFILE_URL)
        self.assertEqual(PostsViewsTests.user, response.context['author'])

    def test_group_on_group_page(self):
        response = self.authorized_client.get(GROUP_URL)
        group = response.context['group']
        self.assertEqual(PostsViewsTests.group.slug, group.slug)
        self.assertEqual(PostsViewsTests.group.title, group.title)
        self.assertEqual(PostsViewsTests.group.description, group.description)

    def test_post_image_in_context(self):
        cases = (
            MAIN_PAGE_URL,
            PROFILE_URL,
            GROUP_URL,
            PostsViewsTests.URL_POST_DETAIL,
        )
        for url in cases:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                if 'page_obj' in response.context:
                    self.assertEqual(
                        PostsViewsTests.post.image,
                        response.context['page_obj'][0].image
                    )
                else:
                    self.assertEqual(
                        PostsViewsTests.post.image,
                        response.context['post'].image
                    )

    def test_comment_on_URL_POST_DETAIL(self):
        response = self.authorized_client.get(PostsViewsTests.URL_POST_DETAIL)
        self.assertIn(PostsViewsTests.comment, response.context['comments'])

    def test_cashe(self):
        Post.objects.create(
            text='Ещё один пост для тестов',
            author=PostsViewsTests.user
        )
        response = self.authorized_client.get(MAIN_PAGE_URL)
        Post.objects.last().delete()
        self.assertEqual(
            response.content,
            self.authorized_client.get(MAIN_PAGE_URL).content
        )
        cache.clear()
        self.assertNotEqual(
            response.content,
            self.authorized_client.get(MAIN_PAGE_URL).content
        )

    def test_authorize_follow(self):
        count_folow_relations = Follow.objects.count()
        self.authorized_client3.get(PostsViewsTests.PROFILE_FOLLOW)
        self.assertEqual(count_folow_relations + 1, Follow.objects.count())

    def test_authorize_unfollow(self):
        count_folow_relations = Follow.objects.count()
        self.authorized_client.get(PostsViewsTests.PROFILE_UNFOLLOW)
        self.assertEqual(count_folow_relations - 1, Follow.objects.count())


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

    def setUp(self):
        self.client = Client()
        self.client.force_login(user=PaginatorViewsTest.user)

    def test_first_page_contains_some_records(self):
        names = [
            MAIN_PAGE_URL,
            GROUP_URL,
            PROFILE_URL
        ]
        for name in names:
            with self.subTest(name=name):
                response = self.client.get(name)
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
                response = self.client.get(name + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 1)
