import json
import requests

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


def geocode(address):
    """Геокодирование через Nominatim (OpenStreetMap). Возвращает (lat, lng) или (None, None)."""
    if not address:
        return None, None
    # Пропускаем явно онлайн-форматы
    low = address.strip().lower()
    if low in ("онлайн", "удалённо", "remote", "online", "—", "-"):
        return None, None

    def _query(q):
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1, "accept-language": "ru"},
                headers={"User-Agent": "tramplin-app/1.0"},
                timeout=8,
            )
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            pass
        return None, None

    # Попытка 1: оригинальный адрес
    lat, lng = _query(address)
    if lat is not None:
        return lat, lng

    # Попытка 2: убираем почтовый индекс и лишние слова (ДОМ, д., кв. и т.д.)
    import re
    simplified = re.sub(r'\b\d{6}\b', '', address)           # почтовый индекс
    simplified = re.sub(r'\b(ДОМ|д\.|кв\.|стр\.|корп\.)\s*', '', simplified, flags=re.IGNORECASE)
    simplified = re.sub(r',\s*,', ',', simplified).strip(', ')
    if simplified != address:
        lat, lng = _query(simplified)
        if lat is not None:
            return lat, lng

    # Попытка 3: только город (первый токен до запятой или первые 2 слова)
    parts = [p.strip() for p in address.split(',') if p.strip()]
    if len(parts) > 1:
        # берём последние части где обычно город/страна
        for city_candidate in reversed(parts):
            if len(city_candidate) > 2:
                lat, lng = _query(city_candidate)
                if lat is not None:
                    return lat, lng

    return None, None


class User(AbstractUser):
    ROLE_SEEKER = "seeker"
    ROLE_EMPLOYER = "employer"
    ROLE_CURATOR = "curator"
    ROLE_CHOICES = [
        (ROLE_SEEKER, "Соискатель"),
        (ROLE_EMPLOYER, "Работодатель"),
        (ROLE_CURATOR, "Куратор"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_SEEKER)
    is_blocked = models.BooleanField("Заблокирован", default=False)
    blocked_reason = models.CharField("Причина блокировки", max_length=300, blank=True)
    display_name = models.CharField("Отображаемое имя", max_length=150, blank=True)

    # Employer verification fields
    inn = models.CharField("ИНН", max_length=12, blank=True)
    corporate_email = models.EmailField("Корпоративный email", blank=True)
    professional_network_url = models.URLField("Ссылка на профиль (LinkedIn/Habr)", blank=True)
    is_verified_employer = models.BooleanField("Верифицированный работодатель", default=False)

    # Employer profile
    company_name = models.CharField("Название компании", max_length=200, blank=True)
    company_description = models.TextField("Краткое описание", blank=True)
    company_industry = models.CharField("Отрасль", max_length=100, blank=True)
    company_website = models.URLField("Сайт компании", blank=True)
    company_video_url = models.URLField("Видео-презентация (YouTube/Vimeo)", blank=True)

    # Seeker profile
    university = models.CharField("Университет", max_length=200, blank=True)
    graduation_year = models.CharField("Год выпуска / Курс", max_length=20, blank=True)
    skills = models.TextField("Навыки (через запятую)", blank=True)
    github_url = models.URLField("GitHub / GitLab", blank=True)
    portfolio_url = models.URLField("Портфолио", blank=True)
    about = models.TextField("О себе", blank=True)

    def __str__(self):
        return self.display_name or self.username

    @property
    def skills_list(self):
        return [s.strip() for s in (self.skills or "").split(",") if s.strip()]

    @property
    def is_curator(self):
        return self.role == self.ROLE_CURATOR

    @property
    def is_superadmin(self):
        return self.is_superuser

    # Privacy settings
    is_profile_public = models.BooleanField("Публичный профиль (нетворкинг)", default=False)

    # Mentor flag — set automatically when a MentorApplication is approved
    is_mentor = models.BooleanField(
        "Верифицированный ментор",
        default=False,
        db_index=True,
        help_text="Устанавливается автоматически при одобрении заявки на менторство.",
    )

    # Mentor activity tracking
    MENTOR_STATUS_AVAILABLE = "available"
    MENTOR_STATUS_BUSY = "busy"
    MENTOR_STATUS_CHOICES = [
        (MENTOR_STATUS_AVAILABLE, "Доступен"),
        (MENTOR_STATUS_BUSY, "Занят"),
    ]
    mentor_status = models.CharField(
        "Статус ментора",
        max_length=20,
        choices=MENTOR_STATUS_CHOICES,
        default=MENTOR_STATUS_AVAILABLE,
        db_index=True,
        help_text="Автоматически переключается в «Занят» при 3 днях неактивности.",
    )
    last_message_sent_at = models.DateTimeField(
        "Последнее сообщение отправлено",
        null=True,
        blank=True,
        help_text="Обновляется автоматически при каждой отправке сообщения ментором.",
    )

    # Avatar
    avatar = models.FileField(
        "Фото профиля",
        upload_to="avatars/",
        blank=True,
        null=True,
    )

    # Favorites: static opportunity IDs from the OPPORTUNITIES list (stored as JSON)
    favorite_ids = models.TextField("Избранные вакансии (JSON)", default="[]", blank=True)

    @property
    def avatar_url(self):
        """Returns avatar URL or empty string (templates use |default filter)."""
        if self.avatar:
            return self.avatar.url
        return ""

    @property
    def mentorship_status(self):
        """Return the current MentorApplication status for this user.

        Returns MentorApplication.STATUS_NOT_APPLIED if no application exists.
        """
        try:
            return self.mentor_application.status
        except MentorApplication.DoesNotExist:
            return MentorApplication.STATUS_NOT_APPLIED


class Opportunity(models.Model):
    TYPE_VACANCY = "vacancy"
    TYPE_INTERNSHIP = "internship"
    TYPE_EVENT = "event"
    TYPE_MENTORSHIP = "mentorship"
    TYPE_CHOICES = [
        (TYPE_VACANCY, "Вакансия"),
        (TYPE_INTERNSHIP, "Стажировка"),
        (TYPE_EVENT, "Мероприятие"),
        (TYPE_MENTORSHIP, "Менторская программа"),
    ]

    FORMAT_REMOTE = "remote"
    FORMAT_HYBRID = "hybrid"
    FORMAT_OFFICE = "office"
    FORMAT_CHOICES = [
        (FORMAT_REMOTE, "Удалённо"),
        (FORMAT_HYBRID, "Гибрид"),
        (FORMAT_OFFICE, "Офис"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_PLANNED = "planned"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Активна"),
        (STATUS_CLOSED, "Закрыта"),
        (STATUS_PLANNED, "Запланирована"),
    ]

    MODERATION_PENDING = "pending"
    MODERATION_APPROVED = "approved"
    MODERATION_REJECTED = "rejected"
    MODERATION_CHOICES = [
        (MODERATION_PENDING, "На модерации"),
        (MODERATION_APPROVED, "Одобрено"),
        (MODERATION_REJECTED, "Отклонено"),
    ]

    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="opportunities")
    title = models.CharField("Название", max_length=200)
    type = models.CharField("Тип", max_length=20, choices=TYPE_CHOICES, default=TYPE_VACANCY)
    format = models.CharField("Формат", max_length=20, choices=FORMAT_CHOICES, default=FORMAT_REMOTE)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    moderation_status = models.CharField(
        "Статус модерации", max_length=20,
        choices=MODERATION_CHOICES, default=MODERATION_PENDING
    )
    salary = models.CharField("Зарплата / Вознаграждение", max_length=100, blank=True)
    location = models.CharField("Город / Адрес", max_length=200, blank=True)
    latitude = models.FloatField("Широта", null=True, blank=True)
    longitude = models.FloatField("Долгота", null=True, blank=True)
    description = models.TextField("Описание")
    requirements = models.TextField("Требования", blank=True)
    skills_required = models.TextField("Необходимые навыки (через запятую)", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField("Дата окончания", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.employer.company_name or self.employer.display_name}"

    @property
    def skills_list(self):
        return [s.strip() for s in (self.skills_required or "").split(",") if s.strip()]

    @property
    def type_label(self):
        labels = {
            "vacancy": "Вакансия",
            "internship": "Стажировка",
            "event": "Мероприятие",
            "mentorship": "Менторская программа",
        }
        return labels.get(self.type, self.type)

    @property
    def format_label(self):
        labels = {"remote": "Удалённо", "hybrid": "Гибрид", "office": "Офис"}
        return labels.get(self.format, self.format)


class Application(models.Model):
    STATUS_NEW = "new"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_RESERVE = "reserve"
    STATUS_CHOICES = [
        (STATUS_NEW, "Новая"),
        (STATUS_ACCEPTED, "Принят"),
        (STATUS_REJECTED, "Отклонён"),
        (STATUS_RESERVE, "В резерве"),
    ]

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    cover_letter = models.TextField("Сопроводительное письмо", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("opportunity", "applicant")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.applicant} → {self.opportunity}"


class Contact(models.Model):
    """Contact request between two seekers. pending → accepted lifecycle."""
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает подтверждения"),
        (STATUS_ACCEPTED, "Принят"),
    ]

    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="contacts_sent"
    )
    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="contacts_received"
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} [{self.status}]"


class CompanyProfile(models.Model):
    """Extended culture & tech stack data for an employer's company page."""
    employer = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="company_profile"
    )
    # Cover / office photo URL (external link or relative path)
    cover_image_url = models.URLField("Обложка (URL фото офиса)", blank=True)
    # Tech stack stored as JSON: {"Backend": ["Go","Python"], "Frontend": ["React","Next.js"], ...}
    tech_stack_json = models.TextField("Технологии (JSON)", default="{}", blank=True)
    # Core values stored as JSON list: [{"emoji":"🚀","title":"...","desc":"..."}]
    values_json = models.TextField("Ценности (JSON)", default="[]", blank=True)
    # Perks stored as JSON list: [{"icon":"💻","title":"MacBook Pro"}]
    perks_json = models.TextField("Преимущества (JSON)", default="[]", blank=True)
    # Social links
    linkedin_url = models.URLField("LinkedIn компании", blank=True)
    telegram_url = models.URLField("Telegram-канал", blank=True)
    vk_url = models.URLField("ВКонтакте", blank=True)
    # Location text
    office_address = models.CharField("Адрес офиса", max_length=300, blank=True)
    office_latitude = models.FloatField("Широта офиса", null=True, blank=True)
    office_longitude = models.FloatField("Долгота офиса", null=True, blank=True)
    founded_year = models.CharField("Год основания", max_length=10, blank=True)
    team_size = models.CharField("Размер команды", max_length=50, blank=True)

    def __str__(self):
        return f"Профиль компании: {self.employer.company_name or self.employer.display_name}"

    @property
    def tech_stack(self):
        try:
            return json.loads(self.tech_stack_json or "{}")
        except (ValueError, TypeError):
            return {}

    @property
    def values(self):
        try:
            return json.loads(self.values_json or "[]")
        except (ValueError, TypeError):
            return []

    @property
    def perks(self):
        try:
            return json.loads(self.perks_json or "[]")
        except (ValueError, TypeError):
            return []


class CompanyReview(models.Model):
    """User review for a company."""
    company = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews",
        limit_choices_to={"role": "employer"}
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews_written"
    )
    rating = models.PositiveSmallIntegerField("Оценка (1–5)", default=5)
    text = models.TextField("Текст отзыва")
    vacancy_tag = models.CharField("Вакансия (опционально)", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_moderated = models.BooleanField("Прошёл модерацию", default=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("company", "author")

    def __str__(self):
        return f"{self.author} → {self.company.company_name}: {self.rating}★"


class Message(models.Model):
    """Direct message between two users, with optional file attachment."""
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages_sent"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages_received"
    )
    text = models.TextField("Текст", blank=True)
    file_attachment = models.FileField(
        "Вложение", upload_to="chat_attachments/%Y/%m/", blank=True, null=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.sender} → {self.receiver} [{self.timestamp:%d.%m %H:%M}]"

    @property
    def file_name(self):
        if self.file_attachment:
            return self.file_attachment.name.split("/")[-1]
        return ""

    @property
    def is_image(self):
        if self.file_attachment:
            ext = self.file_name.rsplit(".", 1)[-1].lower()
            return ext in ("jpg", "jpeg", "png", "gif", "webp")
        return False


# ── Автогеокодинг ─────────────────────────────────────────────────────────────

@receiver(pre_save, sender=Opportunity)
def reset_opportunity_coords_on_location_change(sender, instance, **kwargs):
    """Сбрасывает координаты если адрес изменился."""
    if instance.pk:
        try:
            old = Opportunity.objects.get(pk=instance.pk)
            if old.location != instance.location:
                instance.latitude = None
                instance.longitude = None
        except Opportunity.DoesNotExist:
            pass


@receiver(post_save, sender=Opportunity)
def geocode_opportunity(sender, instance, **kwargs):
    """Геокодирует location при сохранении, если координаты ещё не заданы."""
    if instance.location and (instance.latitude is None or instance.longitude is None):
        lat, lng = geocode(instance.location)
        if lat is not None:
            Opportunity.objects.filter(pk=instance.pk).update(latitude=lat, longitude=lng)


@receiver(pre_save, sender=CompanyProfile)
def reset_company_coords_on_address_change(sender, instance, **kwargs):
    """Сбрасывает координаты если адрес офиса изменился."""
    if instance.pk:
        try:
            old = CompanyProfile.objects.get(pk=instance.pk)
            if old.office_address != instance.office_address:
                instance.office_latitude = None
                instance.office_longitude = None
        except CompanyProfile.DoesNotExist:
            pass


@receiver(post_save, sender=CompanyProfile)
def geocode_company_profile(sender, instance, **kwargs):
    """Геокодирует office_address при сохранении, если координаты ещё не заданы."""
    if instance.office_address and (instance.office_latitude is None or instance.office_longitude is None):
        lat, lng = geocode(instance.office_address)
        if lat is not None:
            CompanyProfile.objects.filter(pk=instance.pk).update(
                office_latitude=lat, office_longitude=lng
            )


# ── Активность ментора ────────────────────────────────────────────────────────

@receiver(post_save, sender=Message)
def update_mentor_last_message(sender, instance, created, **kwargs):
    """При каждом новом сообщении от ментора обновляет last_message_sent_at
    и сбрасывает статус обратно в «Доступен», если он был «Занят»."""
    if not created:
        return
    sender_user = instance.sender
    if not sender_user.is_mentor:
        return
    # Используем update() чтобы не триггерить лишние сигналы
    User.objects.filter(pk=sender_user.pk).update(
        last_message_sent_at=instance.timestamp,
        mentor_status=User.MENTOR_STATUS_AVAILABLE,
    )


class Recommendation(models.Model):
    """Opportunity recommendation sent from one user to a contact."""
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommendations_sent"
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommendations_received"
    )
    opportunity_id = models.IntegerField("ID вакансии")
    opportunity_title = models.CharField("Название вакансии", max_length=200)
    opportunity_company = models.CharField("Компания", max_length=200)
    message = models.TextField("Сообщение", blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender} → {self.recipient}: {self.opportunity_title}"


class MentorApplication(models.Model):
    """Application submitted by a seeker who wishes to become a mentor.

    One-to-one with User: each user may have at most one mentor application.
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_NOT_APPLIED = "not_applied"

    STATUS_CHOICES = [
        (STATUS_PENDING, "На рассмотрении"),
        (STATUS_APPROVED, "Одобрено"),
        (STATUS_REJECTED, "Отклонено"),
        (STATUS_NOT_APPLIED, "Не подавал заявку"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="mentor_application",
        verbose_name="Пользователь",
    )
    status = models.CharField(
        "Статус заявки",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    experience_description = models.TextField(
        "Описание опыта",
        help_text="Расскажите о своём профессиональном опыте и достижениях.",
    )
    skills_to_teach = models.TextField(
        "Навыки для передачи",
        help_text="Перечислите навыки и технологии, которым вы готовы обучать.",
    )
    applied_at = models.DateTimeField("Дата подачи заявки", auto_now_add=True)

    # Privacy consent — must be explicitly accepted before submission
    accepted_privacy_policy = models.BooleanField(
        "Политика конфиденциальности ментора принята",
        default=False,
        help_text="Пользователь принял Политику конфиденциальности программы менторства.",
    )
    accepted_terms_of_service = models.BooleanField(
        "Условия использования приняты",
        default=False,
        help_text="Пользователь принял Условия использования программы менторства.",
    )

    class Meta:
        verbose_name = "Заявка на менторство"
        verbose_name_plural = "Заявки на менторство"
        ordering = ["-applied_at"]

    def __str__(self):
        return f"Заявка на менторство: {self.user} [{self.get_status_display()}]"

    @property
    def is_approved(self):
        """Convenience check used in templates and business logic."""
        return self.status == self.STATUS_APPROVED

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING
