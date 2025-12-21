from django import forms
from .models import Thread, Reply, Tag

class ThreadForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple,  
        required=False,
        label="Pilih Tag"
    )

    class Meta:
        model = Thread
        fields = ['title', 'content', 'tags'] 


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ['content']
