from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import RegistrationForm, LoginForm, EmployerProfileForm, SeekerProfileForm, OpportunityForm, CompanyProfileForm, CompanyReviewForm, AvatarUploadForm
from .models import User, Opportunity, Application, Contact, Recommendation, CompanyProfile, CompanyReview, Message, MentorApplication
from .recommendations import get_recommended_opportunities, get_matched_seekers
import json


# ── Rich opportunity dataset shared across views ──────────────────────────────
OPPORTUNITIES = [
    {
        "id": 1,
        "title": "Python Backend Developer",
        "company": "Яндекс",
        "logo": "Я", "color": "#FC3F1D",
        "type": "vacancy",        # vacancy | internship | mentorship | event
        "type_label": "Вакансия Middle+",
        "format": "remote",
        "salary": "250 000 — 350 000 ₽",
        "salary_min": 250000,
        "location": "Москва (или удалённо)",
        "lat": 55.7558, "lng": 37.6173,
        "description": "Разрабатываем высоконагруженные сервисы для 100 млн пользователей. Ищем опытного бэкенд-разработчика в команду Поиска.",
        "requirements": "Опыт от 3 лет, знание Python 3.10+, asyncio, опыт с PostgreSQL и Redis.",
        "skills": ["Python", "Django", "PostgreSQL", "Redis", "asyncio"],
        "level_tags": ["Middle", "Senior"],
        "published": "15 мар 2026",
        "expires": "15 апр 2026",
        "contact_name": "Анна Смирнова",
        "contact_email": "jobs@yandex-team.ru",
        "contact_url": "https://yandex.ru/jobs",
    },
    {
        "id": 2,
        "title": "Frontend Engineer (React)",
        "company": "Сбер",
        "logo": "С", "color": "#21A038",
        "type": "vacancy",
        "type_label": "Вакансия Junior+",
        "format": "hybrid",
        "salary": "180 000 — 260 000 ₽",
        "salary_min": 180000,
        "location": "Москва, ул. Вавилова 19",
        "lat": 55.7300, "lng": 37.5800,
        "description": "Команда SberTech ищет фронтенд-разработчика для работы над флагманским продуктом СберБанк Онлайн.",
        "requirements": "React 18+, TypeScript, знание GraphQL будет плюсом. Опыт от 1 года.",
        "skills": ["React", "TypeScript", "GraphQL", "CSS"],
        "level_tags": ["Junior", "Middle"],
        "published": "18 мар 2026",
        "expires": "18 апр 2026",
        "contact_name": "Дмитрий Козлов",
        "contact_email": "hr@sbertech.ru",
        "contact_url": "https://sber.ru/career",
    },
    {
        "id": 3,
        "title": "DevOps / Platform Engineer",
        "company": "VK",
        "logo": "VK", "color": "#0077FF",
        "type": "vacancy",
        "type_label": "Вакансия Senior",
        "format": "office",
        "salary": "300 000 — 420 000 ₽",
        "salary_min": 300000,
        "location": "Санкт-Петербург, Невский пр. 28",
        "lat": 59.9311, "lng": 30.3609,
        "description": "Строим платформу для деплоя тысяч микросервисов. Нужен инженер с глубоким пониманием Kubernetes и облачных технологий.",
        "requirements": "Kubernetes, Terraform, CI/CD, опыт с AWS или GCP. Опыт от 4 лет.",
        "skills": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD"],
        "level_tags": ["Senior", "Lead"],
        "published": "10 мар 2026",
        "expires": "10 апр 2026",
        "contact_name": "Елена Фёдорова",
        "contact_email": "jobs@vk.team",
        "contact_url": "https://team.vk.company/jobs",
    },
    {
        "id": 4,
        "title": "Стажёр — Data Science",
        "company": "Тинькофф",
        "logo": "Т", "color": "#FFDD2D",
        "type": "internship",
        "type_label": "Стажировка",
        "format": "hybrid",
        "salary": "80 000 — 120 000 ₽",
        "salary_min": 80000,
        "location": "Москва, Москва-Сити",
        "lat": 55.7900, "lng": 37.5400,
        "description": "Оплачиваемая стажировка в команде ML-платформы. Работаешь над реальными задачами с первого дня.",
        "requirements": "Знание Python, основы ML (sklearn, pandas). Студент 3–5 курса или выпускник.",
        "skills": ["Python", "ML", "pandas", "SQL", "sklearn"],
        "level_tags": ["Intern", "Junior"],
        "published": "20 мар 2026",
        "expires": "20 мая 2026",
        "contact_name": "Мария Иванова",
        "contact_email": "internship@tinkoff.ru",
        "contact_url": "https://tinkoff.ru/career",
    },
    {
        "id": 5,
        "title": "iOS Developer (Swift)",
        "company": "Авито",
        "logo": "А", "color": "#00AAFF",
        "type": "vacancy",
        "type_label": "Вакансия Middle",
        "format": "remote",
        "salary": "220 000 — 300 000 ₽",
        "salary_min": 220000,
        "location": "Новосибирск (удалённо)",
        "lat": 54.9885, "lng": 82.9207,
        "description": "Разрабатываем нативное iOS-приложение с 40 млн активных пользователей. Команда мобильной разработки.",
        "requirements": "Swift 5.9+, SwiftUI, UIKit, опыт с CoreData и сетевыми запросами. Опыт от 2 лет.",
        "skills": ["Swift", "SwiftUI", "UIKit", "CoreData", "Xcode"],
        "level_tags": ["Middle"],
        "published": "12 мар 2026",
        "expires": "12 апр 2026",
        "contact_name": "Игорь Петров",
        "contact_email": "mobile@avito.ru",
        "contact_url": "https://avito.ru/company/jobs",
    },
    {
        "id": 6,
        "title": "Менторская программа — Go Backend",
        "company": "Wildberries",
        "logo": "W", "color": "#CB11AB",
        "type": "mentorship",
        "type_label": "Менторская программа",
        "format": "remote",
        "salary": "Бесплатно",
        "salary_min": 0,
        "location": "Онлайн",
        "lat": 55.6800, "lng": 37.4900,
        "description": "3-месячная программа менторства для разработчиков, желающих перейти на Go. Персональный ментор из команды WB Tech.",
        "requirements": "Базовые знания любого языка программирования. Готовность уделять 10 ч/нед.",
        "skills": ["Go", "gRPC", "Kafka", "PostgreSQL"],
        "level_tags": ["Junior", "Middle"],
        "published": "1 мар 2026",
        "expires": "1 июн 2026",
        "contact_name": "Команда WB Tech",
        "contact_email": "mentor@wb.ru",
        "contact_url": "https://tech.wildberries.ru",
    },
    {
        "id": 7,
        "title": "Хакатон: AI для городской среды",
        "company": "Правительство Москвы",
        "logo": "М", "color": "#E63946",
        "type": "event",
        "type_label": "Мероприятие",
        "format": "office",
        "salary": "Призовой фонд 1 000 000 ₽",
        "salary_min": 0,
        "location": "Москва, Технополис Москва",
        "lat": 55.6500, "lng": 37.7200,
        "description": "48-часовой хакатон по разработке AI-решений для умного города. Командное участие, 3–5 человек.",
        "requirements": "Любой уровень. Нужны разработчики, дизайнеры, аналитики данных.",
        "skills": ["Python", "ML", "Computer Vision", "FastAPI"],
        "level_tags": ["Junior", "Middle", "Senior"],
        "published": "5 мар 2026",
        "expires": "5 апр 2026",
        "contact_name": "Оргкомитет",
        "contact_email": "hack@mos.ru",
        "contact_url": "https://hackmos.ru",
    },
    {
        "id": 8,
        "title": "UX/UI Designer",
        "company": "Ростелеком",
        "logo": "Р", "color": "#FF6600",
        "type": "vacancy",
        "type_label": "Вакансия Middle",
        "format": "hybrid",
        "salary": "150 000 — 210 000 ₽",
        "salary_min": 150000,
        "location": "Казань, ул. Баумана 44",
        "lat": 55.7887, "lng": 49.1221,
        "description": "Проектируем интерфейсы для B2B и B2C продуктов. Ищем дизайнера с сильным портфолио и системным мышлением.",
        "requirements": "Figma, опыт проектирования сложных интерфейсов, знание дизайн-систем. Опыт от 2 лет.",
        "skills": ["Figma", "Prototyping", "Design Systems", "User Research"],
        "level_tags": ["Middle"],
        "published": "17 мар 2026",
        "expires": "17 апр 2026",
        "contact_name": "HR Ростелеком",
        "contact_email": "career@rt.ru",
        "contact_url": "https://rt.ru/career",
    },
    {
        "id": 9,
        "title": "Product Manager — EdTech",
        "company": "Skyeng",
        "logo": "S", "color": "#7C3AED",
        "type": "vacancy",
        "type_label": "Вакансия Middle+",
        "format": "remote",
        "salary": "200 000 — 280 000 ₽",
        "salary_min": 200000,
        "location": "Удалённо (вся Россия)",
        "lat": 55.8200, "lng": 37.6800,
        "description": "Развиваем продукт для 2 млн учеников. Ищем PM с опытом в EdTech или B2C продуктах.",
        "requirements": "Опыт в продуктовой роли от 2 лет, умение работать с данными, Agile/Scrum.",
        "skills": ["Product Management", "Agile", "Analytics", "Figma", "SQL"],
        "level_tags": ["Middle", "Senior"],
        "published": "22 мар 2026",
        "expires": "22 апр 2026",
        "contact_name": "Skyeng Talent",
        "contact_email": "jobs@skyeng.ru",
        "contact_url": "https://skyeng.ru/jobs",
    },
    {
        "id": 10,
        "title": "Стажёр — Java Backend",
        "company": "Сбер",
        "logo": "С", "color": "#21A038",
        "type": "internship",
        "type_label": "Стажировка",
        "format": "office",
        "salary": "70 000 — 100 000 ₽",
        "salary_min": 70000,
        "location": "Москва, ул. Кутузовская 32",
        "lat": 55.7400, "lng": 37.5600,
        "description": "Стажировка в команде платёжных систем СберТех. Работа с высоконагруженными Java-сервисами.",
        "requirements": "Java Core, Spring Boot (базовый уровень), SQL. Студент или выпускник.",
        "skills": ["Java", "Spring Boot", "SQL", "Maven"],
        "level_tags": ["Intern"],
        "published": "19 мар 2026",
        "expires": "30 апр 2026",
        "contact_name": "SberTech HR",
        "contact_email": "intern@sbertech.ru",
        "contact_url": "https://sber.ru/career/internship",
    },
]


SKILL_TAGS = ["Python", "JavaScript", "React", "Go", "Java", "SQL",
              "Figma", "DevOps", "iOS", "ML", "TypeScript", "Kotlin"]

DIRECTIONS = [
    {"name": "Python Developer",    "count": 312},
    {"name": "Frontend Developer",  "count": 287},
    {"name": "Data Analyst",        "count": 198},
    {"name": "Backend Developer",   "count": 176},
    {"name": "ML Engineer",         "count": 154},
    {"name": "DevOps Engineer",     "count": 132},
    {"name": "UI/UX Designer",      "count": 118},
    {"name": "iOS Developer",       "count": 97},
    {"name": "Android Developer",   "count": 89},
    {"name": "QA Engineer",         "count": 76},
    {"name": "Product Manager",     "count": 64},
    {"name": "Кибербезопасность",   "count": 58},
]

TOP_EMPLOYERS = [
    {"name": "Яндекс",    "logo": "Я",  "color": "#FC3F1D", "count_label": "47 вакансий"},
    {"name": "Сбер",      "logo": "С",  "color": "#21A038", "count_label": "38 вакансий"},
    {"name": "Тинькофф",  "logo": "Т",  "color": "#FFDD2D", "count_label": "29 вакансий"},
    {"name": "VK",        "logo": "VK", "color": "#0077FF", "count_label": "24 вакансии"},
    {"name": "Kaspersky", "logo": "K",  "color": "#006D5B", "count_label": "18 вакансий"},
    {"name": "Озон",      "logo": "О",  "color": "#005BFF", "count_label": "22 вакансии"},
    {"name": "Авито",     "logo": "А",  "color": "#00AAFF", "count_label": "15 вакансий"},
    {"name": "МТС",       "logo": "М",  "color": "#E30611", "count_label": "12 вакансий"},
]


def home(request):
    from django.db.models import Count, Q

    approved = Opportunity.objects.filter(
        moderation_status=Opportunity.MODERATION_APPROVED,
        status=Opportunity.STATUS_ACTIVE,
    ).select_related("employer").order_by("-created_at")

    # Serialize for JS map/list
    opps_list = []
    for o in approved:
        opps_list.append({
            "id": o.pk,
            "title": o.title,
            "company": o.employer.company_name or o.employer.display_name or o.employer.username,
            "logo": (o.employer.company_name or o.employer.display_name or "?")[:2].upper(),
            "color": "#2563EB",
            "type": o.type,
            "type_label": o.type_label,
            "format": o.format,
            "salary": o.salary,
            "salary_min": 0,
            "location": o.location or "Не указано",
            "lat": None,
            "lng": None,
            "description": o.description,
            "requirements": o.requirements,
            "skills": o.skills_list,
            "level_tags": [],
            "published": o.created_at.strftime("%d %b %Y").lstrip("0") if o.created_at else "",
            "expires": o.expires_at.strftime("%d %b %Y").lstrip("0") if o.expires_at else "—",
            "contact_name": o.employer.display_name or o.employer.username,
            "contact_email": o.employer.corporate_email or o.employer.email,
            "contact_url": o.employer.company_website or "#",
            "employer_id": o.employer.pk,
        })

    # Top employers: those with most approved active opportunities
    top_employers = (
        User.objects.filter(role="employer")
        .annotate(opp_count=Count(
            "opportunities",
            filter=Q(opportunities__moderation_status=Opportunity.MODERATION_APPROVED,
                     opportunities__status=Opportunity.STATUS_ACTIVE)
        ))
        .filter(opp_count__gt=0)
        .order_by("-opp_count")[:8]
    )

    # Skill tags: collect from approved opportunities
    all_skills = set()
    for o in approved:
        all_skills.update(o.skills_list)
    skill_tags = sorted(all_skills)[:16]

    context = {
        "opportunities_json": json.dumps(opps_list, ensure_ascii=False),
        "total": len(opps_list),
        "skill_tags": skill_tags,
        "top_employers": top_employers,
    }
    return render(request, "tramplin/home.html", context)


@login_required
def apply_for_opportunity(request, opp_id):
    """Handle POST application submission for a DB-backed Opportunity."""
    if request.method != "POST":
        return redirect("tramplin:home")

    user = request.user
    if user.role != "seeker":
        messages.error(request, "Только соискатели могут откликаться на вакансии.")
        return redirect(request.META.get("HTTP_REFERER", "tramplin:home"))

    opp = get_object_or_404(
        Opportunity,
        pk=opp_id,
        moderation_status=Opportunity.MODERATION_APPROVED,
    )

    already_applied = Application.objects.filter(opportunity=opp, applicant=user).exists()
    if already_applied:
        messages.warning(request, "Вы уже откликались на эту вакансию.")
        return redirect(request.META.get("HTTP_REFERER", "tramplin:home"))

    cover_letter = request.POST.get("cover_letter", "").strip()
    Application.objects.create(
        opportunity=opp,
        applicant=user,
        cover_letter=cover_letter,
        status=Application.STATUS_NEW,
    )
    messages.success(request, "Ваш отклик успешно отправлен!")
    return redirect(request.META.get("HTTP_REFERER", "tramplin:home"))


@login_required
def apply_mentor(request):
    """Display and process the mentor application form."""
    user = request.user

    # Redirect non-seekers — only seekers can apply for mentorship
    if user.role != User.ROLE_SEEKER:
        messages.error(request, "Программа менторства доступна только для соискателей.")
        return redirect("tramplin:seeker_dashboard")

    # If an application already exists, redirect back with a notice
    existing = MentorApplication.objects.filter(user=user).first()
    if existing:
        status_label = existing.get_status_display()
        messages.info(request, f"Ваша заявка уже подана. Текущий статус: {status_label}.")
        return redirect("tramplin:seeker_dashboard")

    if request.method == "POST":
        experience = request.POST.get("experience_description", "").strip()
        skills = request.POST.get("skills_to_teach", "").strip()
        privacy = request.POST.get("accepted_privacy_policy") == "on"
        tos = request.POST.get("accepted_terms_of_service") == "on"

        errors = []
        if not experience:
            errors.append("Пожалуйста, опишите ваш опыт.")
        if not skills:
            errors.append("Пожалуйста, укажите навыки для передачи.")
        if not privacy:
            errors.append("Необходимо принять Политику конфиденциальности.")
        if not tos:
            errors.append("Необходимо принять Условия использования.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "tramplin/apply_mentor.html", {
                "experience": experience,
                "skills": skills,
            })

        MentorApplication.objects.create(
            user=user,
            experience_description=experience,
            skills_to_teach=skills,
            accepted_privacy_policy=privacy,
            accepted_terms_of_service=tos,
            status=MentorApplication.STATUS_PENDING,
        )
        messages.success(request, "Ваша заявка на менторство успешно подана! Мы рассмотрим её в ближайшее время.")
        return redirect("tramplin:seeker_dashboard")

    return render(request, "tramplin/apply_mentor.html")


@login_required
def mentor_set_available(request):
    """POST: ментор сбрасывает статус «Занят» → «Доступен» вручную.
    Также обновляет last_message_sent_at на текущее время, чтобы
    команда check_mentor_activity не переключила его снова немедленно."""
    if request.method != "POST":
        return redirect("tramplin:seeker_dashboard")
    user = request.user
    if not user.is_mentor:
        return redirect("tramplin:seeker_dashboard")
    from django.utils import timezone
    User.objects.filter(pk=user.pk).update(
        mentor_status=User.MENTOR_STATUS_AVAILABLE,
        last_message_sent_at=timezone.now(),
    )
    messages.success(request, "Ваш статус ментора изменён на «Доступен».")
    return redirect("tramplin:seeker_dashboard")


def vacancies(request):
    db_vacancies = Opportunity.objects.filter(
        type=Opportunity.TYPE_VACANCY,
        moderation_status=Opportunity.MODERATION_APPROVED,
    ).select_related("employer").order_by("-created_at")

    from django.db.models import Count
    featured_companies = (
        db_vacancies.values(
            "employer__id", "employer__company_name",
            "employer__company_description", "employer__company_industry",
        )
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )

    # Serialize for map
    map_points = []
    for o in db_vacancies:
        if o.latitude and o.longitude:
            map_points.append({
                "lat": o.latitude, "lng": o.longitude,
                "title": o.title,
                "company": o.employer.company_name or o.employer.display_name or o.employer.username,
                "location": o.location,
                "salary": o.salary,
                "format": o.format_label,
                "url": f"/company/{o.employer.pk}/",
            })

    applied_ids = set()
    if request.user.is_authenticated and request.user.role == "seeker":
        applied_ids = set(
            Application.objects.filter(applicant=request.user)
            .values_list("opportunity_id", flat=True)
        )

    context = {
        "vacancies": db_vacancies,
        "featured_companies": featured_companies,
        "total": db_vacancies.count(),
        "map_points_json": json.dumps(map_points, ensure_ascii=False),
        "applied_ids": applied_ids,
    }
    return render(request, "tramplin/vacancies.html", context)


def events(request):
    from django.utils import timezone
    today = timezone.now().date()

    db_events = Opportunity.objects.filter(
        type=Opportunity.TYPE_EVENT,
        moderation_status=Opportunity.MODERATION_APPROVED,
    ).select_related("employer").order_by("-created_at")

    from django.db.models import Count
    featured_companies = (
        db_events.values(
            "employer__id", "employer__company_name",
            "employer__company_description", "employer__company_industry",
        )
        .annotate(count=Count("id"))
        .order_by("-count")[:6]
    )

    map_points = []
    for o in db_events:
        if o.latitude and o.longitude:
            map_points.append({
                "lat": o.latitude, "lng": o.longitude,
                "title": o.title,
                "company": o.employer.company_name or o.employer.display_name or o.employer.username,
                "location": o.location,
                "salary": o.salary,
                "format": o.format_label,
                "url": f"/company/{o.employer.pk}/",
            })

    applied_ids = set()
    if request.user.is_authenticated and request.user.role == "seeker":
        applied_ids = set(
            Application.objects.filter(applicant=request.user)
            .values_list("opportunity_id", flat=True)
        )

    context = {
        "events": db_events,
        "featured_companies": featured_companies,
        "total": db_events.count(),
        "today": today,
        "map_points_json": json.dumps(map_points, ensure_ascii=False),
        "applied_ids": applied_ids,
    }
    return render(request, "tramplin/events.html", context)


def internships(request):
    # DB-backed approved internships
    db_internships = Opportunity.objects.filter(
        type=Opportunity.TYPE_INTERNSHIP,
        moderation_status=Opportunity.MODERATION_APPROVED,
    ).select_related("employer").order_by("-created_at")

    # Featured companies: employers who have approved internships
    from django.db.models import Count
    featured_companies = (
        db_internships.values(
            "employer__id", "employer__company_name",
            "employer__company_description", "employer__company_industry",
        )
        .annotate(count=Count("id"))
        .order_by("-count")[:6]
    )

    map_points = []
    for o in db_internships:
        if o.latitude and o.longitude:
            map_points.append({
                "lat": o.latitude, "lng": o.longitude,
                "title": o.title,
                "company": o.employer.company_name or o.employer.display_name or o.employer.username,
                "location": o.location,
                "salary": o.salary,
                "format": o.format_label,
                "url": f"/company/{o.employer.pk}/",
            })

    applied_ids = set()
    if request.user.is_authenticated and request.user.role == "seeker":
        applied_ids = set(
            Application.objects.filter(applicant=request.user)
            .values_list("opportunity_id", flat=True)
        )

    context = {
        "internships": db_internships,
        "featured_companies": featured_companies,
        "total": db_internships.count(),
        "map_points_json": json.dumps(map_points, ensure_ascii=False),
        "applied_ids": applied_ids,
    }
    return render(request, "tramplin/internships.html", context)


# ── Auth views ────────────────────────────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect("tramplin:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("tramplin:dashboard")
    return render(request, "tramplin/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("tramplin:dashboard")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            if user.is_blocked:
                reason = user.blocked_reason or "Обратитесь к администратору."
                form.add_error(None, f"Ваш аккаунт заблокирован. {reason}")
            else:
                remember = form.cleaned_data.get("remember_me")
                if not remember:
                    request.session.set_expiry(0)
                login(request, user)
                return redirect("tramplin:dashboard")
    return render(request, "tramplin/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("tramplin:login")


@login_required
def dashboard(request):
    """Role-based redirect to the correct dashboard."""
    if request.user.role == "employer":
        return redirect("tramplin:employer_dashboard")
    return redirect("tramplin:seeker_dashboard")


# ── Employer Dashboard ────────────────────────────────────────────────────────

@login_required
def employer_dashboard(request):
    if request.user.role != "employer":
        return redirect("tramplin:seeker_dashboard")

    user = request.user
    profile_form = EmployerProfileForm(instance=user)
    opp_form = OpportunityForm()
    company_profile_obj, _ = CompanyProfile.objects.get_or_create(employer=user)
    company_profile_form = CompanyProfileForm(instance=company_profile_obj)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_profile":
            profile_form = EmployerProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профиль компании обновлён.")
                return redirect("tramplin:employer_dashboard")
        elif action == "upload_avatar":
            avatar_form = AvatarUploadForm(request.POST, request.FILES, instance=user)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, "Фото профиля обновлено.")
            else:
                for err in avatar_form.errors.get("avatar", []):
                    messages.error(request, err)
            return redirect("tramplin:employer_dashboard")
        elif action == "delete_avatar":
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save(update_fields=["avatar"])
            messages.success(request, "Фото профиля удалено.")
            return redirect("tramplin:employer_dashboard")
        elif action == "save_company_profile":
            company_profile_form = CompanyProfileForm(request.POST, instance=company_profile_obj)
            if company_profile_form.is_valid():
                company_profile_form.save()
                messages.success(request, "Страница компании обновлена.")
                return redirect("tramplin:employer_dashboard")
        elif action == "create_opportunity":
            opp_form = OpportunityForm(request.POST)
            if opp_form.is_valid():
                opp = opp_form.save(commit=False)
                opp.employer = user
                # Координаты из карты-пикера (если работодатель выбрал точку вручную)
                try:
                    lat = request.POST.get("latitude")
                    lng = request.POST.get("longitude")
                    if lat and lng:
                        opp.latitude = float(lat)
                        opp.longitude = float(lng)
                except (ValueError, TypeError):
                    pass
                opp.save()
                messages.success(request, "Вакансия успешно создана.")
                return redirect("tramplin:employer_dashboard")

    opportunities = Opportunity.objects.filter(employer=user)
    search_q = request.GET.get("q", "")
    if search_q:
        opportunities = opportunities.filter(title__icontains=search_q)

    active_opps = opportunities.filter(status="active")
    closed_opps = opportunities.filter(status="closed")
    planned_opps = opportunities.filter(status="planned")

    # All applications for this employer's opportunities
    all_applications = Application.objects.filter(
        opportunity__employer=user
    ).select_related("applicant", "opportunity")

    app_search = request.GET.get("app_q", "")
    if app_search:
        all_applications = all_applications.filter(
            applicant__display_name__icontains=app_search
        )

    # Reverse matching: rank applicants by skill fit
    matched_seekers = get_matched_seekers(user)

    context = {
        "profile_form": profile_form,
        "opp_form": opp_form,
        "company_profile_form": company_profile_form,
        "active_opps": active_opps,
        "closed_opps": closed_opps,
        "planned_opps": planned_opps,
        "all_applications": all_applications,
        "search_q": search_q,
        "app_search": app_search,
        "total_opps": opportunities.count(),
        "total_apps": all_applications.count(),
        "matched_seekers": matched_seekers,
    }
    return render(request, "tramplin/employer_dashboard.html", context)


@login_required
def edit_opportunity(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk, employer=request.user)
    form = OpportunityForm(request.POST or None, instance=opp)
    if request.method == "POST" and form.is_valid():
        updated_opp = form.save(commit=False)
        try:
            lat = request.POST.get("latitude")
            lng = request.POST.get("longitude")
            if lat and lng:
                updated_opp.latitude = float(lat)
                updated_opp.longitude = float(lng)
        except (ValueError, TypeError):
            pass
        updated_opp.save()
        messages.success(request, "Вакансия обновлена.")
        return redirect("tramplin:employer_dashboard")
    return render(request, "tramplin/edit_opportunity.html", {"form": form, "opp": opp})


@login_required
def update_application_status(request, pk):
    app = get_object_or_404(Application, pk=pk, opportunity__employer=request.user)
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Application.STATUS_CHOICES):
            app.status = new_status
            app.save()
    return redirect("tramplin:employer_dashboard")


# ── Seeker Dashboard ──────────────────────────────────────────────────────────

@login_required
def seeker_dashboard(request):
    if request.user.role != "seeker":
        return redirect("tramplin:employer_dashboard")

    user = request.user
    profile_form = SeekerProfileForm(instance=user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_profile":
            profile_form = SeekerProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профиль обновлён.")
                return redirect("tramplin:seeker_dashboard")

        elif action == "upload_avatar":
            avatar_form = AvatarUploadForm(request.POST, request.FILES, instance=user)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, "Фото профиля обновлено.")
            else:
                for err in avatar_form.errors.get("avatar", []):
                    messages.error(request, err)
            return redirect("tramplin:seeker_dashboard")

        elif action == "delete_avatar":
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save(update_fields=["avatar"])
            messages.success(request, "Фото профиля удалено.")
            return redirect("tramplin:seeker_dashboard")

        elif action == "toggle_privacy":
            user.is_profile_public = not user.is_profile_public
            user.save(update_fields=["is_profile_public"])
            status = "публичным" if user.is_profile_public else "приватным"
            messages.success(request, f"Профиль стал {status}.")
            return redirect("tramplin:seeker_dashboard")

    my_applications = Application.objects.filter(
        applicant=user
    ).select_related("opportunity", "opportunity__employer")

    # Contacts this user follows (accepted only)
    my_contacts = Contact.objects.filter(
        from_user=user, status=Contact.STATUS_ACCEPTED
    ).select_related("to_user")

    # Incoming pending requests
    pending_requests = Contact.objects.filter(
        to_user=user, status=Contact.STATUS_PENDING
    ).select_related("from_user")

    # Incoming recommendations
    inbox = Recommendation.objects.filter(
        recipient=user
    ).select_related("sender").order_by("-created_at")
    unread_count = inbox.filter(is_read=False).count()

    # Favorites from static list
    try:
        fav_ids = set(json.loads(user.favorite_ids or "[]"))
    except (ValueError, TypeError):
        fav_ids = set()
    favorites = [o for o in OPPORTUNITIES if o["id"] in fav_ids]

    # Recommendation engine
    recommended_raw = get_recommended_opportunities(user)
    # Split into high (>60%) for the "Recommended" section
    recommended = [r for r in recommended_raw if r["score"] > 60]

    context = {
        "profile_form": profile_form,
        "my_applications": my_applications,
        "skills_list": user.skills_list,
        "my_contacts": my_contacts,
        "pending_requests": pending_requests,
        "inbox": inbox,
        "unread_count": unread_count,
        "favorites": favorites,
        "opportunities_json": json.dumps(OPPORTUNITIES),
        "recommended": recommended,
    }
    return render(request, "tramplin/seeker_dashboard.html", context)


@login_required
def toggle_favorite(request):
    """Add/remove a static opportunity from user's favorites via POST."""
    if request.method == "POST":
        opp_id = int(request.POST.get("opp_id", 0))
        user = request.user
        try:
            fav_ids = set(json.loads(user.favorite_ids or "[]"))
        except (ValueError, TypeError):
            fav_ids = set()
        if opp_id in fav_ids:
            fav_ids.discard(opp_id)
            added = False
        else:
            fav_ids.add(opp_id)
            added = True
        user.favorite_ids = json.dumps(list(fav_ids))
        user.save(update_fields=["favorite_ids"])
        return JsonResponse({"added": added, "count": len(fav_ids)})
    return JsonResponse({"error": "method not allowed"}, status=405)


@login_required
def send_contact_request(request, user_id):
    """Send a contact request (pending) to any user."""
    target = get_object_or_404(User, pk=user_id)
    if target != request.user:
        Contact.objects.get_or_create(
            from_user=request.user,
            to_user=target,
            defaults={"status": Contact.STATUS_PENDING},
        )
    return redirect("tramplin:public_profile", user_id=user_id)


@login_required
def accept_contact_request(request, user_id):
    """Accept an incoming contact request from user_id."""
    contact = get_object_or_404(
        Contact, from_user_id=user_id, to_user=request.user, status=Contact.STATUS_PENDING
    )
    contact.status = Contact.STATUS_ACCEPTED
    contact.save(update_fields=["status"])
    # Create the reverse link so both sides see each other as contacts
    Contact.objects.get_or_create(
        from_user=request.user,
        to_user_id=user_id,
        defaults={"status": Contact.STATUS_ACCEPTED},
    )
    return redirect("tramplin:public_profile", user_id=user_id)


@login_required
def add_contact(request, user_id):
    """Legacy: kept for backward compat (networking page). Creates accepted contact."""
    target = get_object_or_404(User, pk=user_id)
    if target != request.user:
        Contact.objects.get_or_create(
            from_user=request.user,
            to_user=target,
            defaults={"status": Contact.STATUS_ACCEPTED},
        )
    return redirect("tramplin:seeker_dashboard")


@login_required
def remove_contact(request, user_id):
    """Remove contact in both directions."""
    Contact.objects.filter(from_user=request.user, to_user_id=user_id).delete()
    Contact.objects.filter(from_user_id=user_id, to_user=request.user).delete()
    referer = request.META.get("HTTP_REFERER", "")
    if f"/profile/{user_id}/" in referer:
        return redirect("tramplin:public_profile", user_id=user_id)
    if request.user.role == "employer":
        return redirect("tramplin:employer_dashboard")
    return redirect("tramplin:seeker_dashboard")


@login_required
def send_recommendation(request):
    if request.method == "POST":
        recipient_id = request.POST.get("recipient_id")
        opp_id = int(request.POST.get("opp_id", 0))
        opp_title = request.POST.get("opp_title", "")
        opp_company = request.POST.get("opp_company", "")
        msg = request.POST.get("message", "")
        recipient = get_object_or_404(User, pk=recipient_id)
        Recommendation.objects.create(
            sender=request.user,
            recipient=recipient,
            opportunity_id=opp_id,
            opportunity_title=opp_title,
            opportunity_company=opp_company,
            message=msg,
        )
        messages.success(request, f"Рекомендация отправлена пользователю {recipient.display_name or recipient.username}.")
    return redirect("tramplin:seeker_dashboard")


@login_required
def mark_recommendations_read(request):
    Recommendation.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("tramplin:seeker_dashboard")


@login_required
def chat_send(request):
    """POST: send a message (text and/or file) to another user."""
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    receiver_id = request.POST.get("receiver_id")
    text = request.POST.get("text", "").strip()
    file = request.FILES.get("file")

    if not receiver_id:
        return JsonResponse({"error": "receiver_id required"}, status=400)
    if not text and not file:
        return JsonResponse({"error": "empty message"}, status=400)

    receiver = get_object_or_404(User, pk=receiver_id)

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "pdf", "doc", "docx", "txt", "zip", "webm", "ogg", "mp3"}
    if file:
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        if ext not in ALLOWED_EXTENSIONS:
            return JsonResponse({"error": "Тип файла не поддерживается"}, status=400)
        if file.size > 10 * 1024 * 1024:
            return JsonResponse({"error": "Файл слишком большой (макс. 10 МБ)"}, status=400)

    msg = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        text=text,
        file_attachment=file or None,
    )
    return JsonResponse({
        "id": msg.pk,
        "sender_id": msg.sender_id,
        "text": msg.text,
        "timestamp": msg.timestamp.strftime("%H:%M"),
        "file_url": msg.file_attachment.url if msg.file_attachment else None,
        "file_name": msg.file_name,
        "is_image": msg.is_image,
    })


@login_required
def chat_messages(request, user_id):
    """GET: messages between current user and user_id. ?since=<id> for polling."""
    other = get_object_or_404(User, pk=user_id)
    since_id = int(request.GET.get("since", 0))

    qs = Message.objects.filter(
        sender__in=[request.user, other],
        receiver__in=[request.user, other],
    )
    if since_id:
        qs = qs.filter(pk__gt=since_id)

    qs.filter(receiver=request.user, is_read=False).update(is_read=True)

    msgs = []
    for m in qs.select_related("sender"):
        msgs.append({
            "id": m.pk,
            "sender_id": m.sender_id,
            "text": m.text,
            "timestamp": m.timestamp.strftime("%H:%M"),
            "file_url": m.file_attachment.url if m.file_attachment else None,
            "file_name": m.file_name,
            "is_image": m.is_image,
        })
    return JsonResponse({"messages": msgs})


@login_required
def chat_unread_count(request):
    """GET: total unread message count for badge polling."""
    count = Message.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({"unread": count})


@login_required
def chat_inbox(request):
    """GET: contacts list with last message snippet and unread count per contact.
    Includes both accepted contacts AND anyone the user has exchanged messages with."""
    from django.db.models import Q

    # Accepted contacts
    contact_ids = set(
        Contact.objects.filter(
            from_user=request.user, status=Contact.STATUS_ACCEPTED
        ).values_list("to_user_id", flat=True)
    )

    # Also include anyone we've messaged or received a message from
    messaged_ids = set(
        Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).exclude(
            Q(sender=request.user, receiver=request.user)
        ).values_list(
            "sender_id", flat=True
        ) | Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).values_list("receiver_id", flat=True)
    ) - {request.user.pk}

    all_ids = contact_ids | messaged_ids

    contacts_data = []
    for uid in all_ids:
        try:
            other = User.objects.get(pk=uid)
        except User.DoesNotExist:
            continue

        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver=other) |
            Q(sender=other, receiver=request.user)
        ).order_by("-timestamp").first()

        unread = Message.objects.filter(
            sender=other, receiver=request.user, is_read=False
        ).count()

        contacts_data.append({
            "id": other.pk,
            "name": other.display_name or other.username,
            "initial": (other.display_name or other.username or "?")[0].upper(),
            "avatar_url": other.avatar_url,
            "last_text": last_msg.text[:60] if last_msg and last_msg.text else ("📎 Файл" if last_msg and last_msg.file_attachment else ""),
            "last_time": last_msg.timestamp.strftime("%H:%M") if last_msg else "",
            "unread": unread,
            "is_mentor": other.is_mentor,
        })

    contacts_data.sort(key=lambda c: c["last_time"], reverse=True)
    return JsonResponse({"contacts": contacts_data})


@login_required
def chat_mini_profile(request, user_id):
    """GET: compact profile data for the chat mini-profile overlay."""
    other = get_object_or_404(User, pk=user_id)
    is_staff = request.user.is_superuser or request.user.role == User.ROLE_CURATOR

    # Employers are always "public" in the mini-profile
    if other.role == User.ROLE_EMPLOYER:
        is_public = True
    else:
        is_public = other.is_profile_public or is_staff

    data = {
        "id": other.pk,
        "name": other.display_name or other.username,
        "initial": (other.display_name or other.username or "?")[0].upper(),
        "avatar_url": other.avatar_url,
        "is_public": is_public,
        "profile_url": f"/profile/{other.pk}/",
        "role": other.role,
    }
    if is_public:
        if other.role == User.ROLE_EMPLOYER:
            data.update({
                "university": other.company_name or "",
                "graduation_year": other.company_industry or "",
                "about": (other.company_description or "")[:120],
                "skills": [],
                "github_url": "",
                "portfolio_url": other.company_website or "",
            })
        else:
            data.update({
                "university": other.university or "",
                "graduation_year": other.graduation_year or "",
                "about": (other.about or "")[:120],
                "skills": other.skills_list[:3],
                "github_url": other.github_url or "",
                "portfolio_url": other.portfolio_url or "",
            })
    return JsonResponse(data)


# Lightweight in-process typing store: {(typer_id, target_id): timestamp}
import time as _time
_TYPING_STORE: dict = {}
_TYPING_TTL = 4  # seconds


@login_required
def chat_typing_signal(request, user_id):
    """POST: record that request.user is typing to user_id.
       GET:  check if user_id is typing to request.user."""
    if request.method == "POST":
        key = (request.user.pk, int(user_id))
        _TYPING_STORE[key] = _time.monotonic()
        return JsonResponse({"ok": True})

    # GET — is user_id typing to me?
    key = (int(user_id), request.user.pk)
    ts  = _TYPING_STORE.get(key, 0)
    is_typing = (_time.monotonic() - ts) < _TYPING_TTL
    return JsonResponse({"typing": is_typing})


@login_required
def chat_presence(request, user_id):
    """GET: lightweight online/offline check — returns last_seen based on recent messages."""
    from django.utils import timezone
    from django.db.models import Q
    other = get_object_or_404(User, pk=user_id)
    # "online" if they sent a message in the last 5 minutes
    cutoff = timezone.now() - timezone.timedelta(minutes=5)
    recent = Message.objects.filter(sender=other, timestamp__gte=cutoff).exists()
    return JsonResponse({
        "online": recent,
        "label": "онлайн" if recent else "был(а) недавно",
    })


@login_required
def public_profile(request, user_id):
    profile_user = get_object_or_404(User, pk=user_id)

    is_staff = request.user.is_authenticated and (
        request.user.is_superuser or request.user.role == User.ROLE_CURATOR
    )
    # Employers always show their public info; privacy setting only applies to seekers
    is_closed = (
        profile_user.role == User.ROLE_SEEKER
        and not profile_user.is_profile_public
        and not is_staff
    )

    # Relationship state: none | pending_sent | pending_received | friends
    rel_state = "none"
    if request.user.is_authenticated and request.user != profile_user:
        outgoing = Contact.objects.filter(from_user=request.user, to_user=profile_user).first()
        incoming = Contact.objects.filter(from_user=profile_user, to_user=request.user).first()
        if outgoing and outgoing.status == Contact.STATUS_ACCEPTED:
            rel_state = "friends"
        elif outgoing and outgoing.status == Contact.STATUS_PENDING:
            rel_state = "pending_sent"
        elif incoming and incoming.status == Contact.STATUS_PENDING:
            rel_state = "pending_received"

    return render(request, "tramplin/public_profile.html", {
        "profile_user": profile_user,
        "is_closed": is_closed,
        "rel_state": rel_state,
    })


@login_required
def public_profiles(request):
    """List of all public seeker profiles for networking discovery."""
    seekers = User.objects.filter(role="seeker", is_profile_public=True).exclude(pk=request.user.pk)

    # ?is_mentor=true — filter to verified mentors only
    mentor_filter = request.GET.get("is_mentor") == "true"
    if mentor_filter:
        seekers = seekers.filter(is_mentor=True)

    my_contact_ids = set(
        Contact.objects.filter(from_user=request.user).values_list("to_user_id", flat=True)
    )
    return render(request, "tramplin/public_profiles.html", {
        "seekers": seekers,
        "my_contact_ids": my_contact_ids,
        "mentor_filter": mentor_filter,
    })


# ── Company Profile (public page) ─────────────────────────────────────────────

def company_profile(request, employer_id):
    employer = get_object_or_404(User, pk=employer_id, role="employer")
    profile, _ = CompanyProfile.objects.get_or_create(employer=employer)
    active_opps = Opportunity.objects.filter(employer=employer, status="active")
    reviews = CompanyReview.objects.filter(company=employer, is_moderated=True).select_related("author")

    # Rating summary
    total_reviews = reviews.count()
    avg_rating = 0
    rating_counts = {i: 0 for i in range(1, 6)}
    if total_reviews:
        total_sum = sum(r.rating for r in reviews)
        avg_rating = round(total_sum / total_reviews, 1)
        for r in reviews:
            rating_counts[r.rating] += 1

    # Review form
    review_form = None
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = CompanyReview.objects.filter(company=employer, author=request.user).exists()
        if not user_has_reviewed:
            review_form = CompanyReviewForm()

    if request.method == "POST" and request.user.is_authenticated:
        action = request.POST.get("action")
        if action == "submit_review" and not user_has_reviewed:
            review_form = CompanyReviewForm(request.POST)
            if review_form.is_valid():
                rev = review_form.save(commit=False)
                rev.company = employer
                rev.author = request.user
                rev.is_moderated = False  # ждёт модерации куратора/суперюзера
                rev.save()
                messages.success(request, "Ваш отзыв отправлен на модерацию и будет опубликован после проверки.")
                return redirect("tramplin:company_profile", employer_id=employer_id)

    # Tech stack badge colors per category
    STACK_COLORS = {
        "Backend":        ("bg-blue-100",   "text-blue-800"),
        "Frontend":       ("bg-violet-100", "text-violet-800"),
        "Data/ML":        ("bg-emerald-100","text-emerald-800"),
        "Infrastructure": ("bg-orange-100", "text-orange-800"),
        "Mobile":         ("bg-pink-100",   "text-pink-800"),
        "Design":         ("bg-yellow-100", "text-yellow-800"),
    }

    context = {
        "employer": employer,
        "profile": profile,
        "tech_stack": profile.tech_stack,
        "values": profile.values,
        "perks": profile.perks,
        "stack_colors": STACK_COLORS,
        "active_opps": active_opps,
        "reviews": reviews,
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "rating_counts": rating_counts,
        "review_form": review_form,
        "user_has_reviewed": user_has_reviewed,
    }
    return render(request, "tramplin/company_profile.html", context)


@login_required
def delete_review(request, review_id):
    """Curators (staff/superuser) can delete any review; authors can delete their own."""
    review = get_object_or_404(CompanyReview, pk=review_id)
    employer_id = review.company_id
    if request.user.is_staff or request.user == review.author:
        review.delete()
        messages.success(request, "Отзыв удалён.")
    return redirect("tramplin:company_profile", employer_id=employer_id)


# ── Companies directory ───────────────────────────────────────────────────────

def companies(request):
    """Public directory of all employer companies with search."""
    from django.db.models import Q, Count
    q = request.GET.get("q", "").strip()
    employers = User.objects.filter(role="employer")

    if q:
        employers = employers.filter(
            Q(company_name__icontains=q) |
            Q(company_industry__icontains=q) |
            Q(opportunities__title__icontains=q)
        ).distinct()

    employers = employers.annotate(
        active_count=Count(
            "opportunities",
            filter=Q(opportunities__status="active")
        )
    ).order_by("-active_count", "company_name")

    return render(request, "tramplin/companies.html", {
        "employers": employers,
        "q": q,
        "total": employers.count(),
    })


# ── Admin Panel ───────────────────────────────────────────────────────────────

def _require_staff(request):
    """Returns True if user is superuser or curator, else False."""
    return request.user.is_authenticated and (
        request.user.is_superuser or request.user.role == User.ROLE_CURATOR
    )


@login_required
def admin_panel(request):
    if not _require_staff(request):
        messages.error(request, "Доступ запрещён.")
        return redirect("tramplin:home")

    from django.db.models import Q, Count

    # Filters
    role_filter = request.GET.get("role", "")
    search_q = request.GET.get("q", "").strip()
    blocked_filter = request.GET.get("blocked", "")

    users = User.objects.exclude(pk=request.user.pk).order_by("date_joined")
    if role_filter:
        users = users.filter(role=role_filter)
    if search_q:
        users = users.filter(
            Q(display_name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(company_name__icontains=search_q)
        )
    if blocked_filter == "1":
        users = users.filter(is_blocked=True)
    elif blocked_filter == "0":
        users = users.filter(is_blocked=False)

    # Pending employer verifications
    pending_employers = User.objects.filter(role="employer", is_verified_employer=False, is_blocked=False)

    # Unmoderated reviews (is_moderated=False means needs review)
    pending_reviews = CompanyReview.objects.filter(is_moderated=False).select_related("author", "company")

    # Pending opportunities awaiting moderation
    pending_opportunities = Opportunity.objects.filter(
        moderation_status=Opportunity.MODERATION_PENDING
    ).select_related("employer").order_by("created_at")

    # Pending mentor applications
    pending_mentor_apps = MentorApplication.objects.filter(
        status=MentorApplication.STATUS_PENDING
    ).select_related("user").order_by("applied_at")

    stats = {
        "total_users": User.objects.count(),
        "seekers": User.objects.filter(role="seeker").count(),
        "employers": User.objects.filter(role="employer").count(),
        "curators": User.objects.filter(role="curator").count(),
        "blocked": User.objects.filter(is_blocked=True).count(),
        "pending_verify": pending_employers.count(),
        "pending_reviews": pending_reviews.count(),
        "pending_opportunities": pending_opportunities.count(),
        "pending_mentors": pending_mentor_apps.count(),
        "approved_mentors": User.objects.filter(is_mentor=True).count(),
    }

    context = {
        "users": users,
        "pending_employers": pending_employers,
        "pending_reviews": pending_reviews,
        "pending_opportunities": pending_opportunities,
        "pending_mentor_apps": pending_mentor_apps,
        "stats": stats,
        "role_filter": role_filter,
        "search_q": search_q,
        "blocked_filter": blocked_filter,
        "role_choices": User.ROLE_CHOICES,
    }
    return render(request, "tramplin/admin_panel.html", context)


@login_required
def admin_set_role(request, user_id):
    """Superuser only: change a user's role."""
    if not request.user.is_superuser:
        messages.error(request, "Только суперпользователь может менять роли.")
        return redirect("tramplin:admin_panel")
    target = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        new_role = request.POST.get("role")
        if new_role in dict(User.ROLE_CHOICES):
            target.role = new_role
            target.save(update_fields=["role"])
            messages.success(request, f"Роль пользователя {target.display_name or target.email} изменена на «{dict(User.ROLE_CHOICES)[new_role]}».")
    return redirect("tramplin:admin_panel")


@login_required
def admin_toggle_block(request, user_id):
    """Superuser or curator: block/unblock a user."""
    if not _require_staff(request):
        messages.error(request, "Доступ запрещён.")
        return redirect("tramplin:home")
    target = get_object_or_404(User, pk=user_id)
    # Curators cannot block other curators or superusers
    if not request.user.is_superuser and (target.is_superuser or target.role == User.ROLE_CURATOR):
        messages.error(request, "Куратор не может блокировать других кураторов или суперпользователей.")
        return redirect("tramplin:admin_panel")
    if request.method == "POST":
        target.is_blocked = not target.is_blocked
        target.blocked_reason = request.POST.get("reason", "").strip()
        target.save(update_fields=["is_blocked", "blocked_reason"])
        action = "заблокирован" if target.is_blocked else "разблокирован"
        messages.success(request, f"Пользователь {target.display_name or target.email} {action}.")
    return redirect("tramplin:admin_panel")


@login_required
def admin_verify_employer(request, user_id):
    """Superuser or curator: verify/unverify an employer."""
    if not _require_staff(request):
        messages.error(request, "Доступ запрещён.")
        return redirect("tramplin:home")
    target = get_object_or_404(User, pk=user_id, role="employer")
    if request.method == "POST":
        target.is_verified_employer = not target.is_verified_employer
        target.save(update_fields=["is_verified_employer"])
        action = "верифицирован" if target.is_verified_employer else "верификация снята"
        messages.success(request, f"Работодатель {target.company_name or target.email}: {action}.")
    return redirect("tramplin:admin_panel")


@login_required
def admin_moderate_review(request, review_id):
    """Superuser or curator: approve or delete a review."""
    if not _require_staff(request):
        messages.error(request, "Доступ запрещён.")
        return redirect("tramplin:home")
    review = get_object_or_404(CompanyReview, pk=review_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            review.is_moderated = True
            review.save(update_fields=["is_moderated"])
            messages.success(request, "Отзыв одобрен и опубликован.")
        elif action == "delete":
            review.delete()
            messages.success(request, "Отзыв удалён.")
    return redirect("tramplin:admin_panel")


@login_required
def admin_moderate_opportunity(request, opp_id):
    """Superuser or curator: approve or reject an opportunity."""
    if not _require_staff(request):
        messages.error(request, "Доступ запрещён.")
        return redirect("tramplin:home")
    opp = get_object_or_404(Opportunity, pk=opp_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            opp.moderation_status = Opportunity.MODERATION_APPROVED
            opp.save(update_fields=["moderation_status"])
            messages.success(request, f"«{opp.title}» одобрено и опубликовано.")
        elif action == "reject":
            opp.moderation_status = Opportunity.MODERATION_REJECTED
            opp.save(update_fields=["moderation_status"])
            messages.success(request, f"«{opp.title}» отклонено.")
    return redirect("tramplin:admin_panel")


@login_required
def admin_moderate_mentor(request, application_id):
    """Superuser or curator: approve or reject a MentorApplication.

    On approval, the applicant's is_mentor flag is set to True.
    On rejection, it is revoked (in case of a re-review after prior approval).
    """
    if not _require_staff(request):
        messages.error(request, "Доступ запрещён.")
        return redirect("tramplin:home")

    application = get_object_or_404(
        MentorApplication.objects.select_related("user"), pk=application_id
    )

    if request.method == "POST":
        action = request.POST.get("action")
        applicant = application.user
        name = applicant.display_name or applicant.username

        if action == "approve":
            application.status = MentorApplication.STATUS_APPROVED
            application.save(update_fields=["status"])
            # Grant mentor status on the user profile
            User.objects.filter(pk=applicant.pk).update(is_mentor=True)
            messages.success(
                request,
                f"Заявка «{name}» одобрена. Статус «Верифицированный ментор» присвоен.",
            )
        elif action == "reject":
            application.status = MentorApplication.STATUS_REJECTED
            application.save(update_fields=["status"])
            # Revoke mentor flag in case it was previously granted
            User.objects.filter(pk=applicant.pk).update(is_mentor=False)
            messages.warning(request, f"Заявка «{name}» отклонена.")

    return redirect("tramplin:admin_panel")
