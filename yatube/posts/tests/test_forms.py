import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, User
from django import forms


USERNAME = 'auth'
SLUG = 'test-slug'
SECOND_SLUG = 'test-slug-2'
URL_POST_CREATE = reverse('posts:post_create')
PROFILE_URL = reverse(
    'posts:profile', args=[USERNAME]
)
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
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug=SLUG,
            description='тестовое описание группы'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовый заголовок 2 группы',
            slug=SECOND_SLUG,
            description='тестовое описание 2 группы'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста 1',
            author=cls.user,
            group=cls.group,
            image=f'{settings.UPLOAD_TO}{cls.uploaded.name}'
        )
        cls.form = PostForm()
        cls.URL_POST_EDIT = reverse(
            'posts:post_edit', args=[cls.post.pk]
        )
        cls.URL_POST_DETAIL = reverse(
            'posts:post_detail', args=[cls.post.pk]
        )
        cls.COMMENT_URL = reverse(
            'posts:add_comment', args=[cls.post.pk]
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        Post.objects.all().delete()
        form_data = {
            'text': 'Тестовый текст поста 2',
            'group': PostFormTests.group.id,
            'image': PostFormTests.uploaded
        }
        response = self.authorized_client.post(
            URL_POST_CREATE,
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), 1)
        self.assertRedirects(response, PROFILE_URL)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                image=f'{settings.UPLOAD_TO}{form_data["image"].name}'
            ).exists()
        )

    def test_post_edit(self):
        """При отправке валидной формы в базе данных меняется пост."""
        form_data = {
            'text': 'Это пост 1, тестовый текст',
            'group': PostFormTests.group_2.id,
        }
        response = self.authorized_client.post(
            PostFormTests.URL_POST_EDIT,
            data=form_data,
            follow=True
        )
        edited_post = response.context['post']
        self.assertRedirects(response, PostFormTests.URL_POST_DETAIL)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.author, PostFormTests.user)
        self.assertEqual(edited_post.group.id, form_data['group'])

    def test_create_page_shows_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(URL_POST_CREATE)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
