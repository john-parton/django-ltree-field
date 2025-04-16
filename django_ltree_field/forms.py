from __future__ import annotations

from typing import TYPE_CHECKING, assert_never

from django import forms
from django.forms.models import modelform_factory as django_modelform_factory
from django.utils.translation import gettext_lazy as _

from django_ltree_field.position import After, Before, FirstChildOf

if TYPE_CHECKING:
    from django_ltree_field.models import AbstractAutoNode


def movenodeform_factory(
    model: AbstractAutoNode,
    *args,
    **kwargs,
):
    class BaseForm(forms.ModelForm):
        position = forms.ChoiceField(
            required=True,
            label=_("Position"),
            choices=[
                ("first-child-of", _("First child of")),
                ("before", _("Before")),
                ("after", _("After")),
            ],
        )
        reference_node = forms.ModelChoiceField(
            queryset=model.objects.all(),
            required=False,
            label=_("Relative to"),
        )

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            if self.instance.id:
                # Set the queryset to exclude the current instance
                self.fields["reference_node"].queryset = model.objects.exclude(
                    pk=self.instance.pk
                )

        def save(self, commit=True):
            instance = super().save(commit=False)

            reference_node = self.cleaned_data["reference_node"]
            position_type = self.cleaned_data.get("position")

            match position_type:
                case "first-child-of":
                    position = FirstChildOf(reference_node)
                case "before":
                    position = Before(reference_node)
                case "after":
                    position = After(reference_node)
                case _:
                    assert_never(position_type)

            instance.move(position)
            if commit:
                instance.save()

            return instance

    if "exclude" not in kwargs:
        kwargs["exclude"] = ("path",)

    return django_modelform_factory(
        model,
        form=BaseForm,
        **kwargs,
    )
