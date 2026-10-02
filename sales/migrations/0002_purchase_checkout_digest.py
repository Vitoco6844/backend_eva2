"""Huella de la solicitud para detectar claves de checkout reutilizadas con otros datos."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sales", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="purchase", name="checkout_digest",
            field=models.CharField(max_length=64, default=""), preserve_default=False,
        ),
    ]
