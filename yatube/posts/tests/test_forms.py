import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post, User
from django import forms


USERNAME = 'auth'
USERNAME2 = 'auth2'
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
SMALL_GIF_2 = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)
TEXT_COMMENT = 'Ура, комментарий отправляется'


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.user2 = User.objects.create_user(username=USERNAME2)
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
        cls.post = Post.objects.create(
            text='Тестовый текст поста 1',
            author=cls.user,
            group=cls.group,
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
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(PostFormTests.user)
        cls.second_authorized_client = Client()
        cls.second_authorized_client.force_login(PostFormTests.user2)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        Post.objects.all().delete()
        uploaded = SimpleUploadedFile(
            name='small1.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст поста 2',
            'group': PostFormTests.group.id,
            'image': uploaded
        }
        response = PostFormTests.authorized_client.post(
            URL_POST_CREATE,
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), 1)
        self.assertRedirects(response, PROFILE_URL)
        new_post = response.context['page_obj'][0]
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.id, form_data['group'])
        self.assertEqual(new_post.author, PostFormTests.user)
        self.assertEqual(
            new_post.image, f'{settings.UPLOAD_TO}{form_data["image"]}'
        )

    def test_post_edit(self):
        """При отправке валидной формы в базе данных меняется пост."""
        uploaded = SimpleUploadedFile(
            name='small3.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Это пост 1, тестовый текст',
            'group': PostFormTests.group_2.id,
            'image': uploaded,
        }
        response = PostFormTests.authorized_client.post(
            PostFormTests.URL_POST_EDIT,
            data=form_data,
            follow=True
        )
        edited_post = response.context['post']
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.author, PostFormTests.post.author)
        self.assertEqual(edited_post.group.id, form_data['group'])
        self.assertEqual(
            edited_post.image.name,
            f'{settings.UPLOAD_TO}{form_data["image"].name}'
        )

    def test_create_page_shows_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = PostFormTests.authorized_client.get(URL_POST_CREATE)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_comment(self):
        Comment.objects.all().delete()
        form_data = {
            'text': TEXT_COMMENT
        }
        response = PostFormTests.authorized_client.post(
            PostFormTests.COMMENT_URL,
            data=form_data,
            follow=True
        )

        self.assertEqual(Comment.objects.count(), 1)
        self.assertRedirects(response, PostFormTests.URL_POST_DETAIL)
        comment = Comment.objects.all()[0]
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, PostFormTests.user)
        self.assertEqual(comment.post_id, PostFormTests.post.pk)

    def test_guest_client_cant_create_post(self):
        Post.objects.all().delete()
        form_data = {
            'text': 'Постов для теста много не бывает'
        }
        PostFormTests.guest_client.post(
            PostFormTests.COMMENT_URL,
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), 0)

    def test_not_author_or_guest_client_edit_post(self):
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        clients = [
            PostFormTests.second_authorized_client,
            PostFormTests.guest_client
        ]
        form_data = {
            'text': 'тестовый текст номер миллион',
            'group': self.group_2.pk,
            'image': uploaded
        }
        for client in clients:
            with self.subTest(client=client):
                client.post(
                    self.URL_POST_EDIT,
                    data=form_data,
                    follow=True,
                )
                edited_post = Post.objects.filter(pk=PostFormTests.post.pk)[0]
                self.assertEqual(PostFormTests.post.author, edited_post.author)
                self.assertEqual(
                    PostFormTests.post.text,
                    edited_post.text
                )
                self.assertEqual(
                    PostFormTests.post.group,
                    edited_post.group
                )
                self.assertEqual(
                    PostFormTests.post.image,
                    edited_post.image
                )
