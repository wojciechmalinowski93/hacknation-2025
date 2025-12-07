from django.core.validators import FileExtensionValidator


def validate_dataset_image_file_extension(value):
    return FileExtensionValidator(allowed_extensions=["jpg", "png", "gif"])(value)
