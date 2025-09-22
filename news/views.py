from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import User, ActivationCode, Article
from .serializers import RegisterSerializer, ArticleSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
import requests
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
from rest_framework.views import APIView

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

@api_view(['POST'])
@permission_classes([AllowAny])
def activate_view(request):
    email = request.data.get('email')
    code = request.data.get('code')
    if not email or not code:
        return Response({'detail': 'email and code required'}, status=400)
    user = get_object_or_404(User, email=email)
    if not hasattr(user, 'activation') or user.activation.code != code:
        return Response({'detail': 'invalid code'}, status=400)
    user.is_active = True
    user.save()
    user.activation.delete()
    return Response({'detail': 'account activated'})

NEWSAPI_KEY = "1b9ed773a8134c5f802187b364841a65"

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def news_list(request):
    q = request.query_params.get('q', 'bitcoin')
    r = requests.get('https://newsapi.org/v2/everything', params={
        'q': q,
        'apiKey': NEWSAPI_KEY,
        'language': 'en'
    }, timeout=10)
    return Response(r.json(), status=r.status_code)



UPDATE_CACHE_KEY = "articles:update_result"
UPDATE_CACHE_TIMEOUT = 60 * 30

class ArticleView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        fresh = request.query_params.get("fresh")
        title_contains = request.query_params.get("title_contains")
        cache_key = f"articles:list:fresh={fresh}:title={title_contains}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = Article.objects.all().order_by("-published_at")
        if fresh and fresh.lower() == "true":
            since = datetime.utcnow() - timedelta(hours=24)
            qs = qs.filter(published_at__gte=since)
        if title_contains:
            qs = qs.filter(title__icontains=title_contains)

        data = ArticleSerializer(qs, many=True).data
        cache.set(cache_key, data, 60 * 10)  
        return Response(data)

    def post(self, request):
        query = request.data.get("q", "technology")
        params = {
            "q": query,
            "language": "en",
            "apiKey": settings.NEWSAPI_KEY,
        }
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        if r.status_code != 200:
            return Response({"error": "NewsAPI error"}, status=r.status_code)

        new_articles = []
        for item in r.json().get("articles", []):
            if not Article.objects.filter(url=item["url"]).exists():
                art = Article.objects.create(
                    source_id=(item["source"]["id"] if item["source"] else None),
                    source_name=item["source"]["name"],
                    author=item.get("author"),
                    title=item.get("title"),
                    description=item.get("description"),
                    url=item.get("url"),
                    url_to_image=item.get("urlToImage"),
                    published_at=datetime.fromisoformat(
                        item["publishedAt"].replace("Z", "+00:00")
                    ),
                    content=item.get("content"),
                )
                new_articles.append(art)

        data = ArticleSerializer(new_articles, many=True).data
        cache.set(UPDATE_CACHE_KEY, data, UPDATE_CACHE_TIMEOUT)  
        return Response({"added": len(new_articles), "articles": data}, status=201)