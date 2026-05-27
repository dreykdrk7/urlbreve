from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def healthz(request):
    return JsonResponse({"status": "ok"})
