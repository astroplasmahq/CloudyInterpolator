# Generated by Django 4.2 on 2023-04-05 23:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feedback", "0003_alter_feedbackmodel_email"),
    ]

    operations = [
        migrations.AlterField(
            model_name="feedbackmodel",
            name="email",
            field=models.EmailField(
                default=None,
                help_text="When we release a new edition of the program, this will make it easier for us to contact you.",
                max_length=254,
                verbose_name="Email Address",
            ),
        ),
        migrations.AlterField(
            model_name="feedbackmodel",
            name="message",
            field=models.TextField(
                default=None,
                help_text="Give your comments here.",
                verbose_name="Message",
            ),
        ),
        migrations.AlterField(
            model_name="feedbackmodel",
            name="name",
            field=models.CharField(
                default=None,
                help_text="We'll refer to you in the communication as such.",
                max_length=128,
                verbose_name="Full Name",
            ),
        ),
    ]
