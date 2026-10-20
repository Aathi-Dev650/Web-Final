from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError
from datetime import datetime, timezone
import json
from pathlib import Path
from .inference import ModelUnavailable, predict_disease
from .models import DiseaseDetection, FarmerProfile


LOW_CONFIDENCE_THRESHOLD = 55


def _database():
    if not settings.MONGODB_URI:
        raise RuntimeError('MongoDB Atlas is not configured. Set MONGODB_URI and restart the server.')
    client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    return client[settings.MONGODB_DATABASE]


def _collection():
    return _database()['crop_analyses']


def _guidance_for(database, prediction):
    """Fetch editorial guidance; the neural network supplies only the class."""
    collection = database['diseases']
    return collection.find_one({'model_label': prediction['label']}) or collection.find_one({
        'crop': prediction['crop'].lower(), 'disease': prediction['disease'].lower()
    })


def _serialize(document):
    # Do not expose any legacy image metadata if old MongoDB records remain.
    for field in ('image_id', 'image_url', 'image_name', 'image_path', 'dropbox_url', 'dropbox_path'):
        document.pop(field, None)
    document['id'] = str(document.pop('_id'))
    return document


def _offline_guidance_for(prediction):
    """Use the reviewed local catalogue when Atlas cannot be reached.

    This keeps the field workflow useful on connections where mobile networks
    block Atlas' database ports. The catalogue is the same one used by the
    MongoDB seeding command; no generated treatment advice is used here.
    """
    from .management.commands.seed_disease_guidance import GUIDANCE
    label = prediction.get('label', '')
    crop = str(prediction.get('crop', '')).lower()
    disease = str(prediction.get('disease', '')).lower()
    return next((item for item in GUIDANCE if item['model_label'] == label), None) or next(
        (item for item in GUIDANCE if item['crop'].lower() == crop and item['disease'].lower() == disease), None
    )


def _local_result(record, guidance=None):
    """Present a SQLite-backed assessment in the same shape as Atlas data."""
    return {
        'id': f'local-{record.pk}',
        'crop': record.crop,
        'disease': record.disease,
        'confidence': record.confidence,
        'status': record.status,
        'needs_retake': record.status == 'Needs review / retake photo',
        'guidance_available': bool(guidance),
        'symptoms': guidance.get('symptoms', []) if guidance else [],
        'solution': guidance.get('solution', []) if guidance else [],
        'prevention': guidance.get('prevention', []) if guidance else [],
        'created_at': record.detected_at.isoformat(),
        'storage': 'local',
    }


@ensure_csrf_cookie
def app_shell(request):
    return render(request, 'disease_detection/app.html')


def supplied_page(request, page):
    """Serve an original supplied UI page without parsing its JS bindings."""
    pages = {'home', 'detection', 'recommend', 'history', 'profile', 'index', 'signup'}
    if page not in pages:
        from django.http import Http404
        raise Http404
    from django.http import HttpResponse
    from pathlib import Path
    page_file = Path(settings.BASE_DIR) / f'{page}.html'
    html = page_file.read_text(encoding='utf-8')
    bridge = '<link rel="stylesheet" href="/static/css/multipage-app.css"><link rel="stylesheet" href="/static/css/tamil-heritage.css"><script src="/static/js/multipage-app.js"></script>'
    return HttpResponse(html.replace('</body>', f'{bridge}</body>'), content_type='text/html; charset=utf-8')


@staff_member_required(login_url='/admin/login/')
def control_centre(request):
    """A compact, staff-only operating view for the local CropCure service."""
    labels_path = Path(settings.DISEASE_LABELS_PATH)
    try:
        labels = json.loads(labels_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        labels = []
    recent = DiseaseDetection.objects.select_related('user').order_by('-detected_at')[:12]
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_analyses': DiseaseDetection.objects.count(),
        'review_count': DiseaseDetection.objects.filter(status='Needs review / retake photo').count(),
        'model_labels': labels,
        'model_available': labels_path.is_file() and Path(settings.DISEASE_MODEL_PATH).is_file(),
        'model_threshold': int(settings.DISEASE_MIN_CONFIDENCE * 100),
        'recent_analyses': recent,
        'users': User.objects.select_related('farmer_profile').order_by('-date_joined')[:12],
        'crop_summary': DiseaseDetection.objects.values('crop').annotate(total=Count('id')).order_by('-total')[:6],
    }
    return render(request, 'disease_detection/control_centre.html', context)


@staff_member_required(login_url='/admin/login/')
def toggle_user_access(request, user_id):
    """Enable/disable a farmer account without exposing privilege escalation."""
    if request.method != 'POST':
        return redirect('control-centre')
    user = get_object_or_404(User, pk=user_id)
    if user == request.user:
        messages.error(request, 'You cannot disable your own administrator account.')
    elif user.is_superuser or user.is_staff:
        messages.error(request, 'Manage staff accounts through Django administration.')
    else:
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        messages.success(request, f"{user.username} is now {'active' if user.is_active else 'disabled'}.")
    return redirect('control-centre')


@api_view(['GET'])
@permission_classes([AllowAny])
def test_api(request):
    return Response({
        "message": "CropCure API is working!",
        "status": "success"
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = str(request.data.get('username', '')).strip().lower()
    password = str(request.data.get('password', ''))
    if len(username) < 3 or len(password) < 8:
        return Response({'detail': 'Username must have 3 characters and password must have 8.'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'detail': 'That username is already in use.'}, status=409)
    email = str(request.data.get('email', '')).strip()
    full_name = str(request.data.get('full_name', '')).strip()
    mobile_number = str(request.data.get('mobile_number', '')).strip()
    district = str(request.data.get('district', '')).strip()
    state = str(request.data.get('state', 'Tamil Nadu')).strip() or 'Tamil Nadu'
    language = str(request.data.get('language', 'English')).strip() or 'English'
    if mobile_number and (not mobile_number.isdigit() or len(mobile_number) != 10):
        return Response({'detail': 'Enter a valid 10-digit mobile number.'}, status=400)
    user = User.objects.create_user(username=username, password=password, email=email)
    user.first_name = full_name
    user.save(update_fields=['first_name'])
    FarmerProfile.objects.create(user=user, mobile_number=mobile_number, district=district, state=state, language=language)
    login(request, user)
    return Response(_user_data(user), status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def session_login(request):
    user = authenticate(request, username=request.data.get('username', ''), password=request.data.get('password', ''))
    if not user:
        return Response({'detail': 'Invalid username or password.'}, status=401)
    login(request, user)
    return Response(_user_data(user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_logout(request):
    logout(request)
    return Response(status=204)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_user(request):
    return Response(_user_data(request.user))


def _user_data(user):
    profile, _ = FarmerProfile.objects.get_or_create(user=user)
    return {
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'email': user.email,
        'mobile_number': profile.mobile_number,
        'district': profile.district,
        'state': profile.state,
        'language': profile.language,
        'joined_at': user.date_joined.isoformat(),
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    profile, _ = FarmerProfile.objects.get_or_create(user=user)
    full_name = str(request.data.get('full_name', user.first_name)).strip()
    user.first_name = full_name
    user.email = str(request.data.get('email', user.email)).strip()
    user.save(update_fields=['first_name', 'email'])
    for field in ('mobile_number', 'district', 'state', 'language'):
        if field in request.data:
            setattr(profile, field, str(request.data[field]).strip())
    profile.save()
    return Response(_user_data(user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_detection(request):
    image = request.FILES.get('image')
    if not image:
        return Response({'detail': 'Please select a leaf image.'}, status=400)
    if not image.content_type or not image.content_type.startswith('image/'):
        return Response({'detail': 'Please upload a valid image file.'}, status=400)
    if image.size > 10 * 1024 * 1024:
        return Response({'detail': 'Image must be smaller than 10 MB.'}, status=400)
    try:
        prediction = predict_disease(image)
    except (ModelUnavailable, ValueError) as exc:
        return Response({'detail': str(exc)}, status=503)
    low_confidence = prediction['confidence'] < LOW_CONFIDENCE_THRESHOLD
    assessment_status = 'Needs review / retake photo' if prediction.get('needs_retake') or low_confidence else ('No Disease Detected' if prediction['disease'].lower() == 'healthy' else 'Disease Detected')
    try:
        database = _database()
        guidance = _guidance_for(database, prediction)
        document = {
            'owner': request.user.username,
            'crop': prediction['crop'],
            'model_label': prediction['label'],
            'disease': prediction['disease'],
            'confidence': prediction['confidence'],
            'status': assessment_status,
            'needs_retake': prediction.get('needs_retake', False),
            'guidance_available': bool(guidance),
            'created_at': datetime.now(timezone.utc),
        }
        if guidance:
            document['symptoms'] = guidance.get('symptoms', [])
            document['solution'] = guidance.get('solution', [])
            document['prevention'] = guidance.get('prevention', [])
        result = database['crop_analyses'].insert_one(document)
        document['_id'] = result.inserted_id
        return Response(_serialize(document), status=status.HTTP_201_CREATED)
    except (RuntimeError, PyMongoError):
        # Atlas is optional for local development. Persist a private, local
        # copy rather than failing the farmer's analysis when a carrier blocks
        # outbound database traffic.
        guidance = _offline_guidance_for(prediction)
        record = DiseaseDetection.objects.create(
            user=request.user,
            crop=prediction['crop'],
            disease=prediction['disease'],
            confidence=prediction['confidence'],
            status=assessment_status,
        )
        return Response(_local_result(record, guidance), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detection_history(request):
    try:
        items = _collection().find({'owner': request.user.username}).sort('created_at', DESCENDING).limit(50)
        return Response([_serialize(item) for item in items])
    except (RuntimeError, PyMongoError):
        records = DiseaseDetection.objects.filter(user=request.user).order_by('-detected_at')[:50]
        return Response([
            _local_result(record, _offline_guidance_for({'crop': record.crop, 'disease': record.disease}))
            for record in records
        ])
