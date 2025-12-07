import os

from dateutil import relativedelta
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _, override, pgettext_lazy
from model_utils import FieldTracker
from modeltrans.fields import TranslationField

from mcod.academy.managers import CourseManager, CourseTrashManager
from mcod.core import storages
from mcod.core.db.managers import TrashManager
from mcod.core.db.models import ExtendedModel, TrashModelBase
from mcod.core.managers import SoftDeletableManager
from mcod.lib.model_sanitization import SanitizedCharField, SanitizedTextField


class Course(ExtendedModel):
    COURSE_STATES = {
        "planned": "Planowane",
        "current": "W trakcie",
        "finished": "Zakończone",
    }
    title = SanitizedCharField(max_length=300, verbose_name=_("title"))
    notes = SanitizedTextField(verbose_name=_("description"))
    venue = SanitizedCharField(max_length=300, verbose_name=_("venue"))
    participants_number = models.PositiveIntegerField(verbose_name=_("number of participants"))
    file = models.FileField(
        verbose_name=_("schedule file"),
        storage=storages.get_storage("courses"),
        upload_to="%Y%m%d",
        max_length=2000,
        null=True,
        blank=True,
    )
    materials_file = models.FileField(
        verbose_name=_("materials file"),
        storage=storages.get_storage("courses_materials"),
        upload_to="%Y%m%d",
        max_length=2000,
        null=True,
        blank=True,
    )

    objects = CourseManager()
    trash = CourseTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    def __str__(self):
        return self.title

    class Meta:
        default_manager_name = "objects"
        verbose_name = _("course")
        verbose_name_plural = _("courses")

    def sessions(self):
        return self.modules.order_by("start")

    @property
    def start(self):
        return self.modules.earliest("start").start

    @property
    def end(self):
        return self.modules.latest("end").end

    @property
    def file_type(self):
        if self.file:
            _name, _ext = os.path.splitext(self.file.name)
            return _ext[1:]

    @property
    def file_url(self):
        return self._get_absolute_url(self.file.url, use_lang=False) if self.file else None

    @property
    def materials_file_type(self):
        if self.materials_file:
            _name, _ext = os.path.splitext(self.materials_file.name)
            return _ext[1:]

    @property
    def materials_file_url(self):
        return self._get_absolute_url(self.materials_file.url, use_lang=False) if self.materials_file else None


class CourseTrash(Course, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash (Courses)")
        verbose_name_plural = _("Trash (Courses)")


class CourseModule(ExtendedModel):
    COURSE_MODULE_TYPES = (
        ("general", pgettext_lazy("General", "academy course module type")),
        ("technical", _("Technical")),
        ("law", _("Law")),
        ("law_technical", _("Law/Technical")),
        ("extra", _("Extra")),
        ("exam", _("Exam")),
    )
    type = models.CharField(max_length=13, choices=COURSE_MODULE_TYPES, verbose_name=_("module type"))
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        verbose_name=_("course"),
        related_name="modules",
    )
    start = models.DateField(verbose_name=_("start date"))
    end = models.DateField(verbose_name=_("end date"))
    number_of_days = models.PositiveIntegerField(
        verbose_name=_("number of days"),
        validators=[MinValueValidator(1), MaxValueValidator(2)],
    )

    objects = SoftDeletableManager()
    trash = TrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    def __str__(self):
        return f"{self.course.title} - {self.get_type_display()}"

    class Meta:
        default_manager_name = "objects"
        verbose_name = _("course module")
        verbose_name_plural = _("course modules")

    @property
    def type_name(self):
        with override("pl"):
            return self.get_type_display()


@receiver(pre_save, sender=CourseModule)
def handle_course_module_pre_save(sender, instance, *args, **kwargs):
    instance.end = instance.start + relativedelta.relativedelta(days=instance.number_of_days - 1)
