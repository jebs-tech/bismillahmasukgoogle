from django.db import models
from django.contrib.auth.models import User


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Thread(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='threads'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='threads')
    created_at = models.DateTimeField(auto_now_add=True)

    # === Tambahan Voting ===
    upvotes = models.ManyToManyField(User, related_name='thread_upvotes', blank=True)
    downvotes = models.ManyToManyField(User, related_name='thread_downvotes', blank=True)

    def total_upvotes(self):
        return self.upvotes.count()

    def total_downvotes(self):
        return self.downvotes.count()

    def score(self):
        # total skor (untuk sorting berdasarkan popularitas)
        return self.total_upvotes() - self.total_downvotes()

    def __str__(self):
        return self.title


class Reply(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # === Tambahan Voting ===
    upvotes = models.ManyToManyField(User, related_name='reply_upvotes', blank=True)
    downvotes = models.ManyToManyField(User, related_name='reply_downvotes', blank=True)

    def total_upvotes(self):
        return self.upvotes.count()

    def total_downvotes(self):
        return self.downvotes.count()

    def score(self):
        return self.total_upvotes() - self.total_downvotes()

    def __str__(self):
        return f"Reply by {self.author.username if self.author else 'Anonim'} on {self.thread.title}"
