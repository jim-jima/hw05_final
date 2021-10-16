from django.contrib.auth.decorators import login_required
from django.core.cache import cache_page

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User
from yatube.settings import POSTS_PER_PAGE


def page_object(request, posts):
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


@cache_page(20)
def index(request):
    post_list = Post.objects.all()
    context = {
        'page_obj': page_object(request, post_list),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    template = 'posts/group_list.html'
    context = {
        'group': group,
        'page_obj': page_object(request, posts),
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    user = get_object_or_404(User, username=username)
    following = False
    if request.user.is_authenticated and request.user.follower.filter(
        author=user
    ).exists():
        following = True
    context = {
        'author': user,
        'page_obj': page_object(request, user.posts.all()),
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    context = {
        'post': post,
        'comments': post.comments.all(),
        'form': CommentForm(request.POST or None),
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user)
    context = {
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        post.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'form': form,
        'post': post,
        'is_edit': 'true',
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.author)
    context = {'page_obj': page_object(request, posts)}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    Follow.objects.create(
        user=request.user,
        author=username
    )


@login_required
def profile_unfollow(request, username):
    Follow.objects.filter(author=username).delete()
