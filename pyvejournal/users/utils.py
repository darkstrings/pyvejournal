from io import BytesIO

from flask import url_for
from flask_mail import Message
from PIL import Image, ImageOps, UnidentifiedImageError

from ..extensions import mail

USERPIC_SIZE = 100  # LiveJournal userpics were 100×100
Image.MAX_IMAGE_PIXELS = 25_000_000  # refuse "decompression bomb" images


class ImageError(ValueError):
    pass


def process_userpic(file_storage) -> bytes:
    """Validate an uploaded image, crop it square, shrink it to 100×100 and re-encode as WebP.

    Re-encoding means we never serve the uploaded bytes themselves (no smuggled scripts,
    no EXIF/GPS metadata leaking).
    """
    try:
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img.seek(0)  # first frame of animated GIFs
        img = ImageOps.exif_transpose(img).convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise ImageError("That file doesn't look like an image we can use.") from e

    img = ImageOps.fit(img, (USERPIC_SIZE, USERPIC_SIZE), method=Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "WEBP", quality=85)
    return out.getvalue()


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Reset your PyveJournal password", recipients=[user.email])
    msg.body = f"""Hi {user.name},

Someone (hopefully you) asked to reset your PyveJournal password. Use this link within 30 minutes:

{url_for('users.reset_token', token=token, _external=True)}

If you didn't ask for this, you can ignore this email — nothing will change.
"""
    mail.send(msg)
